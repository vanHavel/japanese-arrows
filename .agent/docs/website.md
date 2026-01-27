
# Website Architecture
The website is entirely static containing only html, css and js files.
No external CSS or JS libraries are used, everything is self-contained.
The code is separated into html, css and js files in the web/ folder.

# Website navigation
The index page shows the puzzle view for the current day.
The /puzzles/YYYY/MM/DD/ page shows the puzzle view for a specific day.
The /archive page shows the archive view.
The /about page shows the about view.
There is a nav bar at the top for Home and Archive and About.

# Puzzle View
The puzzle View shows the current day's puzzle opened in the editor widget.

Below the puzzle are navigation buttons for previous day (disabled for first day) and next day (if next day <= current date, otherwise disabled).
Between the navigation buttons is the date of the current puzzle.
Below is a share button that copies the url to the clipboard (hint is shown for 2 seconds).

# Editor Widget
The editor widget displays the puzzle as a rectangular grid of arrows. However, grid lines are not shown.
Some of the arrows are filtered with numbers (taken from puzzle.txt) as initial clues. Others need to be filled by the user.
For displaying the arrows, either svg could be used (as in io.py) or some other JS funcionality to draw them. Anyway, the svg can be an inspiration on size, spacing, etc.
The user can click on an arrow to select it, and then hit a digit (0-9) to set the value of the arrow.
Alternatively, there is also a 0-9 numpad to the left of the puzzle for the same purpose.
Hitting backspace or delete removes the value of the selected arrow.
There is also a delete button for this in the numpad.
Below the numpad are buttons pen and pencil (only one can be toggled). Pen is the default mode. When switching to pencil mode, the user can click on an arrow and set a small digit in the center of the arrow. Multiple digits can be set in the same arrow. If setting an digit that is already set, it is removed.
While in Pen mode, pencil mode can also be triggered by pressing the control key, it is then toggled off when the control key is released.
To the right, there are 3 buttons to clear the puzzle (return to initial clues), remove all pencil marks, and to fill the puzzle with the solution.txt.


# Archive View
The archive view shows a paginated list of all puzzles, by default sorted by date descending.
There are filters for difficulty, size and arrow type. The table can be sorted by clicking on the column headers.
Below the table are pagination controls.

# Puzzle Storage
Puzzles are stored in a folder web/puzzles/YYYY/MM/DD.
There are files
- puzzle.txt with text representation of the puzzle
- solution.txt with text representation of the solution
- metadata.yaml with metadata
  - difficulty: Easy (3 complexity, 4x4), Normal (3-4 complexity, 5x5-6x6), Hard (5 complexity, 5x5-6x6), Devious (6 complexity, 6x6)
  - size: 5x5, 6x6
  - arrows: Straight, Diagonal
