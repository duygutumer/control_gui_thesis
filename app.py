import os
from flask import Flask, redirect, request, render_template
import subprocess
import re
from dotenv import dotenv_values  

CONFIG_PATH = "../my_codeless-main/config.py"
PROJECT_CWD = "../my_codeless-main"
PROJECT_ENV_PATH = os.path.join(PROJECT_CWD, ".env")

app = Flask(__name__)

def build_child_env(): # to get he env values from the main project
    env = os.environ.copy()
    # Load the project's .env and overlay
    if os.path.exists(PROJECT_ENV_PATH):
        env.update(dotenv_values(PROJECT_ENV_PATH))
    return env

def update_config_variable(key, value):
    pat = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)(['\"])(.*?)(\2)\s*(#.*)?$")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines, updated = [], False
    for line in lines:
        m = pat.match(line)
        if m:
            prefix, quote, _, _quote2, comment = m.groups()
            safe_val = value.replace("\\", "\\\\").replace(quote, f"\\{quote}")
            new_line = f'{prefix}{quote}{safe_val}{quote}{("" if not comment else " " + comment)}\n'
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'{key} = "{value}"\n')

    # atomic write
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.replace(tmp_path, CONFIG_PATH)


@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        command = request.form.get("command")
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, env=build_child_env())
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


@app.route("/update-news", methods=["POST"])
def update_news():
    if "NEWS_QUERY" in request.form:
            update_config_variable("NEWS_QUERY" , request.form["NEWS_QUERY"])
    return redirect("/")


@app.route("/run-command", methods=["POST"])
def run_command():
    command = request.form.get("command")

    command_map = {
        "install_requirements": ["pip", "install", "-r", "../my_codeless-main/requirements.txt"],
        "run_project": ["python", "../my_codeless-main/run.py"],
        "generate_routes":["python", "../my_codeless-main/generate_routes.py"],
        "run_script": ["python", "../my_codeless-main/script.py"],
        "create_db": ["python", "../my_codeless-main/database.py"],
        "insert_mock_data": ["python", "../my_codeless-main/mock_data.py"],
        "get_news":["python", "../my_codeless-main/news_script.py"],
        "shutdown": ["pkill", "-f", "run.py"],
        "decoy":["python", "../my_codeless-main/decoy_script.py"],
    }

    if command not in command_map:
        return "<pre style='color:red'>Unknown command.</pre>"

    try:
        if command == "run_project":
            subprocess.Popen(command_map[command], cwd="../my_codeless-main", env=build_child_env())
            return f"<pre>Started {command} in background.</pre>"

        output = subprocess.check_output(command_map[command], stderr=subprocess.STDOUT, text=True, cwd="../my_codeless-main", env=build_child_env())
        return f"<pre>{output}</pre>"

    except subprocess.CalledProcessError as e:
        return f"<pre style='color:red'>{e.output}</pre>"

if __name__ == "__main__":
    app.run(port=5001)
