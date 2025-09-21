from flask import Flask, render_template, request, jsonify
import subprocess
import os
import re
from datetime import datetime

app = Flask(__name__)

# Store command history
command_history = []

# Track current working directory
current_directory = os.getcwd()

# Available commands for auto-completion
available_commands = [
    "help", "clear", "history", "ls", "pwd", "cd", "mkdir", "rm", "cat",
    "whoami", "date", "ps", "df", "uname", "echo", "exit"
]

def parse_natural_language(command):
    """
    Parse natural language commands and convert them to shell commands
    """
    lower_command = command.lower().strip()

    # Pattern for creating directory
    mkdir_pattern = re.compile(r'(?:create|make|build)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(\w+)')
    match = mkdir_pattern.search(lower_command)
    if match:
        return f"mkdir {match.group(1)}"

    # Pattern for listing directory contents
    ls_pattern = re.compile(r'(?:list|show)\s+(?:directory|files|contents)(?:\s+of\s+(.+))?')
    match = ls_pattern.search(lower_command)
    if match:
        return f"ls {match.group(1)}" if match.group(1) else "ls"

    # Show current directory
    if re.search(r'(?:show|display)\s+(?:current|working)\s+(?:directory|path)', lower_command):
        return "pwd"

    # Show system info
    if re.search(r'(?:show|display)\s+(?:system|os|info)', lower_command):
        return "uname"

    # Show date/time
    if re.search(r'(?:show|display)\s+(?:date|time)', lower_command):
        return "date"

    # Show user info
    if re.search(r'(?:show|display)\s+(?:user|username)', lower_command):
        return "whoami"

    # Show running processes
    if re.search(r'(?:show|display)\s+(?:processes|running\s+tasks)', lower_command):
        return "ps"

    # Show disk space
    if re.search(r'(?:show|display)\s+(?:disk|space|free\s+space)', lower_command):
        return "df"

    # Creating file
    touch_pattern = re.compile(r'(?:create|make|build)\s+(.*?)(?:\.txt)?\s*(?:file)?')
    match = touch_pattern.search(lower_command)
    if match:
        return f"echo '' > {match.group(1)}"

    # Display file contents
    cat_pattern = re.compile(r'(?:show|display|view)\s+(.*?)(?:\.txt)?\s*(?:file)?')
    match = cat_pattern.search(lower_command)
    if match:
        return f"cat {match.group(1)}"

    # Remove file
    rm_pattern = re.compile(r'(?:delete|remove|erase)\s+(.*?)(?:\.txt)?\s*(?:file)?')
    match = rm_pattern.search(lower_command)
    if match:
        return f"rm {match.group(1)}"

    return command


def execute_command(command):
    """
    Execute a shell command inside the current_directory
    """
    global current_directory

    # Add to history
    command_history.append({
        "command": command,
        "timestamp": datetime.now().isoformat()
    })

    interpreted_command = parse_natural_language(command)

    try:
        # --- Handle special commands ---
        if interpreted_command == "clear":
            return {"output": "", "error": False}

        if interpreted_command == "history":
            output = "\n".join([f"{i+1}: {cmd['command']}" for i, cmd in enumerate(command_history)])
            return {"output": output, "error": False}

        if interpreted_command == "help":
            help_text = """
Available commands:
  help        - Show this help message
  clear       - Clear the terminal
  history     - Show command history
  ls          - List directory contents
  pwd         - Show current directory
  cd <dir>    - Change directory
  mkdir <dir> - Create directory
  rm <file>   - Remove file
  cat <file>  - Display file contents
  whoami      - Show current user
  date        - Show date/time
  ps          - Show running processes
  df          - Show disk space
  uname       - Show system info
  echo <txt>  - Display text
  exit        - Exit terminal
"""
            return {"output": help_text.strip(), "error": False}

        # --- Handle cd ---
        if interpreted_command.startswith("cd "):
            target = interpreted_command[3:].strip()
            new_path = os.path.abspath(os.path.join(current_directory, target))
            if os.path.isdir(new_path):
                current_directory = new_path
                return {"output": f"Changed directory to: {current_directory}", "error": False}
            else:
                return {"output": f"No such directory: {target}", "error": True}

        # --- Map Linux commands to Windows equivalents ---
        if os.name == 'nt':  # Windows
            if interpreted_command.startswith("ls"):
                interpreted_command = interpreted_command.replace("ls", "dir", 1)
            elif interpreted_command.startswith("pwd"):
                interpreted_command = "cd"
            elif interpreted_command.startswith("rm "):
                interpreted_command = interpreted_command.replace("rm", "del", 1)
            elif interpreted_command.startswith("cat "):
                interpreted_command = interpreted_command.replace("cat", "type", 1)
            elif interpreted_command.startswith("uname"):
                interpreted_command = "ver"
            elif interpreted_command.startswith("df"):
                interpreted_command = "wmic logicaldisk get size,freespace,caption"
            elif interpreted_command.startswith("ps"):
                interpreted_command = "tasklist"

        # --- Run the command ---
        result = subprocess.run(
            interpreted_command,
            shell=True,
            cwd=current_directory,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout
        if result.stderr:
            output += result.stderr

        return {"output": output, "error": result.returncode != 0}

    except subprocess.TimeoutExpired:
        return {"output": "Command timed out", "error": True}
    except Exception as e:
        return {"output": f"Error executing command: {str(e)}", "error": True}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/execute", methods=["POST"])
def execute():
    data = request.json
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"output": "No command provided", "error": True})

    result = execute_command(command)
    return jsonify(result)


@app.route("/history", methods=["GET"])
def get_history():
    return jsonify({"history": command_history})


@app.route("/suggest", methods=["POST"])
def suggest():
    data = request.json
    input_text = data.get("input", "").strip().lower()
    suggestions = [cmd for cmd in available_commands if cmd.startswith(input_text)]
    return jsonify({"suggestions": suggestions})


if __name__ == "__main__":
    app.run(debug=True)
