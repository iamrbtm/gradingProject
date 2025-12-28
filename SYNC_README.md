# Assignment Calendar and Reminders Sync

This system allows you to automatically sync your assignments to the **Jeremy-School** calendar and the **Homework** reminders list on macOS. It creates detailed ICS files and uses AppleScript to integrate with macOS Calendar and Reminders apps.

## Features

- **Smart ICS Generation**: Creates comprehensive calendar events with all assignment details
- **Dual Sync**: Syncs to both Calendar and Reminders apps simultaneously
- **Selective Syncing**: Only syncs assignments that are new or have been modified
- **Rich Event Details**: Includes course name, scores, categories, and progress information
- **Automatic Scheduling**: Sets all assignments to be due at 11:59 PM on their due date
- **Priority Setting**: Automatically sets priority based on proximity to due date
- **Reminders with Notes**: Adds detailed notes to reminder items with course and scoring info

## Setup Instructions

### 1. Install Required Dependencies

```bash
pip install icalendar click
```

### 2. Run Database Migration

Before using the sync features, you need to add the sync tracking fields to your database:

```bash
python migrate_sync_fields.py
```

This will add the following fields to your Assignment table:
- `last_synced_calendar`: Timestamp of last calendar sync
- `last_synced_reminders`: Timestamp of last reminders sync
- `calendar_event_id`: ID of the calendar event (for future updates)
- `reminders_item_id`: ID of the reminder item (for future updates)
- `last_modified`: Timestamp of last assignment modification

### 3. Grant Permissions

The first time you run a sync, macOS will ask for permissions to access:
- **Calendar**: To create and modify calendar events
- **Reminders**: To create and modify reminder items

Make sure to grant these permissions when prompted.

## How It Works

### Calendar Sync (`Jeremy-School` Calendar)

Each assignment becomes a calendar event with:
- **Title**: Assignment name
- **Description**: Detailed information including:
  - Assignment name and course
  - Maximum possible score
  - Current score and percentage (if graded)
  - Category and weight information (if applicable)
  - Completion status
- **Location**: Course name
- **Time**: Due date at 11:59 PM (as requested)
- **Alarm**: 30-minute reminder before due time
- **Priority**: Based on how soon the assignment is due:
  - High (1): Due within 1 day
  - Medium (5): Due within 1 week
  - Low (9): Due after 1 week

### Reminders Sync (`Homework` List)

Each assignment becomes a reminder with:
- **Title**: Assignment name
- **Notes**: Same detailed information as calendar description
- **Due Date**: Assignment due date at 11:59 PM
- **Priority**: Same priority system as calendar
- **List**: Added to "Homework" list (created automatically if needed)

### Smart Sync Logic

The system tracks when each assignment was last synced and only re-syncs when:
1. The assignment has never been synced before
2. The assignment has been modified since the last sync
3. You force a complete re-sync

This prevents duplicate entries and reduces unnecessary sync operations.

## Usage

### Web Interface

1. Navigate to the **Sync** page in the web application
2. View sync status and statistics
3. Use the sync buttons to:
   - **Sync All**: Sync to both Calendar and Reminders
   - **Calendar Only**: Sync only to calendar
   - **Reminders Only**: Sync only to reminders
   - **Force Sync All**: Re-sync all assignments regardless of last sync time
4. Export ICS files for manual import
5. Sync individual assignments

### Command Line Interface

```bash
# Sync all pending assignments
flask sync-assignments

# Sync only to calendar
flask sync-assignments --calendar-only

# Sync only to reminders
flask sync-assignments --reminders-only

# Force sync all assignments
flask sync-assignments --force

# Check sync status
flask sync-status

# Export ICS file
flask export-ics --filename my_assignments.ics

# Export ICS file for specific course
flask export-ics --course "Math 101"
```

### Python API

```python
from app.calendar_sync import CalendarSyncManager

# Initialize sync manager
sync_manager = CalendarSyncManager()

# Sync all pending assignments
success, message = sync_manager.sync_all()

# Sync only to calendar
success, message = sync_manager.sync_to_calendar()

# Sync only to reminders
success, message = sync_manager.sync_to_reminders()

# Get assignments that need syncing
assignments_to_sync = sync_manager.get_assignments_to_sync('calendar')

# Create ICS file
ics_file_path = sync_manager.create_ics_file(assignments)
```

## File Locations

- **ICS Files**: Temporary files created in `/tmp/` directory
- **Calendar**: Events added to "Jeremy-School" calendar
- **Reminders**: Items added to "Homework" list

## Troubleshooting

### Permission Issues
- Make sure you've granted Calendar and Reminders permissions to the Terminal or your IDE
- You may need to add your terminal application to Privacy & Security settings

### Sync Failures
- Check that the `icalendar` package is installed
- Verify that Calendar and Reminders apps are available and running
- Check the error messages in the web interface or command line output

### Duplicate Events
- The system should prevent duplicates through smart sync logic
- If you see duplicates, you may need to manually clean up and re-run sync
- Use "Force Sync All" sparingly to avoid overwhelming your calendar

### Missing Assignments
- Only assignments with due dates are synced
- Check that your assignments have proper due dates set
- Verify that the assignments belong to courses in terms for the current user

## Customization

You can customize the sync behavior by modifying `app/calendar_sync.py`:

- **Calendar Name**: Change `self.calendar_name = "Jeremy-School"`
- **Reminders List**: Change `self.reminders_list = "Homework"`
- **Due Time**: Modify the time setting (currently 11:59 PM)
- **Alarm Timing**: Change the 30-minute advance reminder
- **Priority Logic**: Adjust the priority assignment based on due dates

## Security Notes

- The system uses AppleScript to interact with macOS apps
- No sensitive data is stored in calendar or reminder events
- All sync tracking is stored locally in your database
- ICS files are created temporarily and cleaned up after use

## Features for Future Enhancement

- **Update Existing Events**: Modify calendar events when assignments change
- **Delete Completed Assignments**: Remove events for completed assignments
- **Custom Calendars**: Allow users to specify different calendar names
- **Sync Filtering**: More granular control over which assignments to sync
- **Batch Operations**: Efficient handling of large numbers of assignments