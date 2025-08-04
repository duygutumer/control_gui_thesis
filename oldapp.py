from flask import Flask, redirect, render_template, request
import subprocess
import os
import json

# control_gui/app.py

import os
from flask import Flask, request, render_template, redirect
import re

app = Flask(__name__)

CONFIG_PATH = "./config.py"

def update_config_variable(key, value):
    with open(CONFIG_PATH, "r") as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if re.match(f"{key}\s*=", line):
            new_lines.append(f'{key} = "{value}"\n')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'{key} = "{value}"\n')

    with open(CONFIG_PATH, "w") as f:
        f.writelines(new_lines)


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run-script", methods=["POST"])
def run_script():
    script = request.form.get("script")
    script_path = os.path.abspath(os.path.join("..", script))

    try:
        if "run.py" in script:
            subprocess.Popen(["python", script_path], cwd=os.path.dirname(script_path))
            return "<pre> run.py started successfully in the background!</pre>"
        else:
            result = subprocess.check_output(["python", script_path], stderr=subprocess.STDOUT, text=True)
            return f"<pre>{result}</pre>"

    except subprocess.CalledProcessError as e:
        return f"<pre style='color:red'>{e.output}</pre>"
    
@app.route("/update-theme", methods=["POST"])
def update_theme():
    for key in ["PRIMARY_COLOR", "SECONDARY_COLOR", "FONT_FAMILY", "BORDER_RADIUS", "BOX_SHADOW", "BACKGROUND_GRADIENT"]:
        update_config_variable(key, request.form[key])
    return redirect("/")

if __name__ == "__main__":
    app.run(port=5001, debug=True)
