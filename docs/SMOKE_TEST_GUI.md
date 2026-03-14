# Bubbly GUI Smoke Test Checklist

Run this checklist after GUI changes to confirm core flows still work.

1. Launch
1. Run `python bubbly_gui.py`.
1. The window opens without errors.

1. Setup tab: required fields
1. Parser dropdown is populated.
1. Input path, Output folder, Creator, Case are required.
1. Missing required fields show a clear error.

1. Parser change behavior
1. Switching parser updates the Parser Args tab.
1. Parsers with args show fields; parsers without show a hint.
1. Required parser args are marked with `*`.
1. WhatsApp `platform` uses a dropdown with `ios`/`android`.

1. Input selection
1. Browse File and Browse Folder both work.
1. File input works for file-capable parsers (WhatsApp `.txt`, Telegram `.json`, Generic JSON, Romeo DB).
1. Folder input works for folder parsers (Threema, Wire, Telegram).

1. Run flow
1. Clicking Run starts the job.
1. Run button disables; progress bar animates.
1. Logs appear in the Run tab.
1. Status updates on completion.
1. Open Output enables and opens the output folder.

1. Error handling
1. Invalid input path shows an error.
1. Missing required parser arg blocks run.
1. Parser errors show in status/log and GUI stays responsive.

1. Split by chat
1. With split enabled, output contains multiple HTML files.
1. With split disabled, output contains a single HTML.
