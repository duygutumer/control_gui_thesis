from flask import Flask, redirect, request, render_template
import subprocess
import re

CONFIG_PATH = "../my_codeless-main/config.py"

app = Flask(__name__)

def update_config_variable(key, value):
    with open(CONFIG_PATH, "r") as f:
        lines = f.readlines()

    new_lines = []
    updated = False

    for line in lines:
        if re.match(rf"\s*{key}\s*=", line):
            new_lines.append(f'{key} = "{value}"\n')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'{key} = "{value}"\n')

    with open(CONFIG_PATH, "w") as f:
        f.writelines(new_lines)


@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        command = request.form.get("command")
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            result = f"Error:\n{e.output}"
    return render_template("index.html", result=result)

import re

@app.route("/update-theme", methods=["POST"])
def update_theme():
    keys = ["PRIMARY_COLOR", "SECONDARY_COLOR", "BACKGROUND_GRADIENT", "FONT_FAMILY", "BORDER_RADIUS", "BOX_SHADOW"]
    for key in keys:
        if key in request.form:
            update_config_variable(key, request.form[key])
    return redirect("/")


@app.route("/run-command", methods=["POST"])
def run_command():
    command = request.form.get("command")

    command_map = {
        "install_requirements": ["pip", "install", "-r", "../my_codeless-main/requirements.txt"],
        "run_project": ["python", "../my_codeless-main/run.py"],
        "run_script": ["python", "../my_codeless-main/script.py"],
        "create_db": ["python", "../my_codeless-main/database.py"],
        "insert_mock_data": ["python", "../my_codeless-main/mock_data.py"],
        "get_news":["python", "../my_codeless-main/news_script.py"],
        "shutdown": ["pkill", "-f", "run.py"]
    }

    if command not in command_map:
        return "<pre style='color:red'>Unknown command.</pre>"

    try:
        if command == "run_project":
            subprocess.Popen(command_map[command], cwd="../my_codeless-main")
            return f"<pre>Started {command} in background.</pre>"

        output = subprocess.check_output(command_map[command], stderr=subprocess.STDOUT, text=True, cwd="../my_codeless-main")
        return f"<pre>{output}</pre>"

    except subprocess.CalledProcessError as e:
        return f"<pre style='color:red'>{e.output}</pre>"

if __name__ == "__main__":
    app.run(port=5001)
