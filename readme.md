# Asana Offline Backup
Logs into Asana, finds a specifed project, creates an offline backup of that project.

````bash
Usage:
    asana
    asana -t
    asana -e <email>
    asana -p <projects>
    asana -s <save_path>
    asana -u <url>

Options:
    -t      Test login
    -e      Set email login, asking for password separately
    -p      Project class IDs, separated by commas
    -s      Save path
    -u      Url for Asana

Arguments:
    email          Email address
    projects       Class IDs of project to be added, separated by commas
    save_path      The path to save your files to
    url            The login url of Asana
````