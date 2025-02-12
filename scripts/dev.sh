# open a new tmux session
tmux new-session -d -s se25
# run the server in the first pane
tmux send -t 0 "source .venv/bin/activate" ENTER
tmux send -t 0 "python src/api/app.py" ENTER
# split the window horizontally
tmux split-window -h
# run the bot in the second pane
tmux send -t 1 "source .venv/bin/activate" ENTER
tmux send -t 1 "python src/bots/telegram/main.py" ENTER
tmux set mouse on
tmux a -t se25