***

```markdown
# ICS to Google Calendar Importer 📅

A powerful, dual-purpose tool to import extended `.ics` (iCalendar) files directly into your Google Calendar. 

Unlike standard calendar imports, this tool parses **custom metadata** inside your ICS files, allowing you to automatically assign Google Calendar colors, tag events as tasks, and mark items as shiftable/flexible.

## 🌟 Features

- **Standard ICS Parsing:** Reads `SUMMARY`, `DTSTART`, `DTEND`, `DESCRIPTION`, `LOCATION`, and `VALARM` (reminders).
- **Custom Color Mapping:** Reads `X-COLOR-ID` to automatically color-code events in Google Calendar.
- **Custom Metadata:** Reads `X-IS-TASK` and `X-IS-SHIFTABLE` and saves them securely in the event's `extendedProperties.private` for future retrieval or automation.
- **Duplicate Prevention:** Checks for existing events with the same name and start time to update them instead of creating duplicates.

---

## 🛠️ Choose Your Version

This repository contains two completely different ways to use the tool, depending on your technical comfort level:

1. **[Google Apps Script (Web App)](#option-1-the-web-app-no-code-installation)**: Best for regular users. Runs 100% free in your browser. No terminals, no JSON files, no Google Cloud setup.
2. **[Python CLI](#option-2-the-python-cli-for-developers)**: Best for developers and power users who want to run the script locally or automate it via terminal.

---

## Option 1: The Web App (No-Code Installation)

The code in the `google-apps-script` folder allows you to host this tool as a free, private web app using your Google account. 

### Setup Instructions
1. Go to [script.google.com](https://script.google.com/) and click **New Project**.
2. On the left sidebar, click the **+** next to **Services**, select **Google Calendar API**, and click **Add**.
3. Replace the code in the default `Code.gs` file with the contents of `google-apps-script/Code.gs`.
4. Click the **+** next to **Files**, select **HTML**, name it exactly `Index`, and paste the contents of `google-apps-script/Index.html`.
5. In the top right, click **Deploy > New deployment**.
6. Click the gear icon next to "Select type" and choose **Web app**.
7. Set **Execute as** to **User accessing the web app** *(Critical!)*.
8. Set **Who has access** to **Anyone with Google Account**.
9. Click **Deploy**, authorize the permissions, and copy the **Web app URL**.

You can now use this URL on any device, or share it with friends. They will authenticate with their own Google account, and events will go only to their calendar.

---

## Option 2: The Python CLI (For Developers)

The code in the `python-cli` folder is a standalone script for local environments.

### Prerequisites
- Python 3.x installed.
- A Google Cloud Console project.

### Setup Instructions
1. Navigate to the CLI folder and install the dependencies:
   ```bash
   cd python-cli
   pip install -r requirements.txt
   ```
2. Go to the [Google Cloud Console](https://console.cloud.google.com/).
3. Enable the **Google Calendar API** in the API Library.
4. Go to **Credentials**, create an **OAuth client ID** (Application type: "Desktop app").
5. Download the JSON file, rename it to `credentials.json`, and place it inside the `python-cli` folder.
   > **⚠️ SECURITY WARNING:** Never commit your `credentials.json` or `token.json` files to GitHub. Ensure your `.gitignore` is configured correctly.

### Usage
Run the script from your terminal, passing the path to your ICS file:
```bash
python import_calendar.py path/to/your/file.ics
```
On the first run, it will open a browser window to authenticate your Google Account and generate a `token.json` file for future uses.

---

## 📝 Custom ICS Formatting Guide

To utilize the advanced features of this importer, add the following custom `X-` tags to your `VEVENT` blocks inside your `.ics` file:

- `X-COLOR-ID`: Accepts Google Calendar color IDs (e.g., `1` for Lavender, `5` for Banana/Yellow, `11` for Tomato/Red).
- `X-IS-TASK`: Accepts `true` or `false`.
- `X-IS-SHIFTABLE`: Accepts `true` or `false`.

### Example VEVENT:
```text
BEGIN:VEVENT
DTSTART:20260415T070000Z
DTEND:20260415T140000Z
SUMMARY:Development Sprint
DESCRIPTION:Working on the new API endpoints.
X-COLOR-ID:5
X-IS-TASK:true
X-IS-SHIFTABLE:true
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-P0DT0H1M0S
DESCRIPTION:This is an event reminder
END:VALARM
END:VEVENT
```

---

## 🤝 Contributing
Feel free to open issues or submit pull requests if you want to add new features or improve the parsing logic!
```