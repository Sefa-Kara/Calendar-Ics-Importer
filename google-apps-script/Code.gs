// Code.gs

function doGet() {
  // Serves the HTML user interface when someone opens the URL
  return HtmlService.createHtmlOutputFromFile('Index')
      .setTitle('ICS to Google Calendar Importer')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function processICS(icsContent) {
  try {
    const calendarId = 'primary';
    
    // 1. Unfold lines (ICS wraps lines starting with a space or tab)
    const unfoldedContent = icsContent.replace(/\r?\n[ \t]/g, '');
    
    // 2. Split into events
    const eventBlocks = unfoldedContent.split('BEGIN:VEVENT');
    if (eventBlocks.length < 2) return "No events found in file.";

    let createdCount = 0;
    let updatedCount = 0;

    // Skip the first block as it's the calendar header
    for (let i = 1; i < eventBlocks.length; i++) {
      const block = eventBlocks[i];
      
      const summary = extractField(block, 'SUMMARY');
      const dtStart = formatIcsDate(extractField(block, 'DTSTART'));
      const dtEnd = formatIcsDate(extractField(block, 'DTEND'));
      
      if (!summary || !dtStart) continue;

      const eventBody = {
        summary: summary,
        start: { dateTime: dtStart },
        end: dtEnd ? { dateTime: dtEnd } : { dateTime: dtStart },
        description: extractField(block, 'DESCRIPTION') || '',
        location: extractField(block, 'LOCATION') || ''
      };

      // X-COLOR-ID
      const colorId = extractField(block, 'X-COLOR-ID');
      if (colorId) eventBody.colorId = colorId;

      // X-IS-TASK & X-IS-SHIFTABLE -> extendedProperties
      const isTask = extractField(block, 'X-IS-TASK');
      const isShiftable = extractField(block, 'X-IS-SHIFTABLE');
      
      if (isTask || isShiftable) {
        eventBody.extendedProperties = { private: {} };
        if (isTask) eventBody.extendedProperties.private.isTask = isTask.toLowerCase();
        if (isShiftable) eventBody.extendedProperties.private.isShiftable = isShiftable.toLowerCase();
      }

      // Reminders (VALARM)
      if (block.includes('BEGIN:VALARM')) {
        const trigger = extractField(block.split('BEGIN:VALARM')[1], 'TRIGGER');
        if (trigger) {
          const minutes = parseTriggerToMinutes(trigger);
          if (minutes !== null) {
            eventBody.reminders = {
              useDefault: false,
              overrides: [{ method: 'popup', minutes: minutes }]
            };
          }
        }
      }

      // Check for duplicates
      const existingEvents = Calendar.Events.list(calendarId, {
        timeMin: dtStart,
        maxResults: 10,
        q: summary
      }).items;

      let exists = false;
      if (existingEvents && existingEvents.length > 0) {
        for (const ev of existingEvents) {
          if (ev.summary === summary && ev.start.dateTime === dtStart) {
            Calendar.Events.update(eventBody, calendarId, ev.id);
            updatedCount++;
            exists = true;
            break;
          }
        }
      }

      if (!exists) {
        Calendar.Events.insert(eventBody, calendarId);
        createdCount++;
      }
    }

    return `Success! Created ${createdCount} events, updated ${updatedCount} existing events.`;

  } catch (e) {
    return "Error: " + e.message;
  }
}

// --- HELPER FUNCTIONS ---

function extractField(text, fieldName) {
  // Looks for FIELDNAME:value or FIELDNAME;TZID=...:value
  const regex = new RegExp(fieldName + '(?:;[^:]*)?:(.*)', 'i');
  const match = text.match(regex);
  return match ? match[1].trim() : null;
}

function formatIcsDate(dateStr) {
  if (!dateStr) return null;
  // Convert 20260407T140000Z to 2026-04-07T14:00:00Z
  if (dateStr.length >= 15) {
    const y = dateStr.substring(0, 4);
    const m = dateStr.substring(4, 6);
    const d = dateStr.substring(6, 8);
    const h = dateStr.substring(9, 11);
    const min = dateStr.substring(11, 13);
    const s = dateStr.substring(13, 15);
    const z = dateStr.includes('Z') ? 'Z' : ''; 
    return `${y}-${m}-${d}T${h}:${min}:${s}${z}`;
  }
  return null;
}

function parseTriggerToMinutes(triggerStr) {
  // Very basic parser for -P0DT0H1M0S format
  try {
    const match = triggerStr.match(/(\d+)M/);
    if (match) return parseInt(match[1], 10);
    return 10; // default 10 mins if regex fails
  } catch (e) {
    return null;
  }
}