import os
import json
import re
import subprocess
from pathlib import Path

from flask import Flask, redirect, request, render_template, flash
from dotenv import dotenv_values

CONFIG_PATH = "../my_codeless-main/config.py"
PROJECT_CWD = "../my_codeless-main"
PROJECT_ENV_PATH = os.path.join(PROJECT_CWD, ".env")
BRANDS_PATH = os.path.join(PROJECT_CWD, "brands_out.json")

app = Flask(__name__)
app.secret_key = os.getenv("CONTROL_GUI_SECRET", "dev-secret-change-me")


def build_child_env():
    """
    Inherit current env + project's .env so that called scripts
    (generate_routes.py, script.py, etc.) see the same variables.
    """
    env = os.environ.copy()
    if os.path.exists(PROJECT_ENV_PATH):
        env.update(dotenv_values(PROJECT_ENV_PATH))
    return env


def update_config_variable(key, value):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    literal = json.dumps(value, ensure_ascii=False)

    new_lines = []
    updated = False

    for line in lines:
        if re.match(rf"\s*{re.escape(key)}\s*=", line):
            new_lines.append(f"{key} = {literal}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key} = {literal}\n")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)



# ---------- brands_out.json helpers ----------

def load_brands():
    """Load brands_out.json as Python list; return [] if missing."""
    if not os.path.exists(BRANDS_PATH):
        return []
    with open(BRANDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_brands(brands):
    """Write brands list back to brands_out.json with pretty formatting."""
    with open(BRANDS_PATH, "w", encoding="utf-8") as f:
        json.dump(brands, f, ensure_ascii=False, indent=2)


# ---------- routes ----------

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        command = request.form.get("command")
        try:
            result = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True,
                env=build_child_env(),
            )
        except subprocess.CalledProcessError as e:
            result = f"Error:\n{e.output}"

    # load brands list for the “Brand & Style Variant Manager” panel
    try:
        brands = load_brands()
    except Exception as e:
        print(f"Failed to load brands_out.json: {e}")
        brands = []

    return render_template("index.html", result=result, brands=brands)


@app.route("/update-theme", methods=["POST"])
def update_theme():
    keys = [
        "PRIMARY_COLOR",
        "SECONDARY_COLOR",
        "BACKGROUND_GRADIENT",
        "FONT_FAMILY",
        "BORDER_RADIUS",
        "BOX_SHADOW",
    ]
    for key in keys:
        if key in request.form and request.form[key]:
            update_config_variable(key, request.form[key])
    flash("Theme configuration updated.")
    return redirect("/")



@app.route("/run-command", methods=["POST"])
def run_command():
    command = request.form.get("command")

    command_map = {
        "install_requirements": [
            "pip",
            "install",
            "-r",
            "../my_codeless-main/requirements.txt",
        ],
        "run_project": ["python", "../my_codeless-main/run.py"],
        "generate_routes": ["python", "../my_codeless-main/generate_routes.py"],
        "run_script": ["python", "../my_codeless-main/script.py"],
        "create_db": ["python", "../my_codeless-main/database.py"],
        "insert_mock_data": ["python", "../my_codeless-main/mock_data.py"],
        "get_news": ["python", "../my_codeless-main/news_script.py"],
        "shutdown": ["pkill", "-f", "run.py"],
        "decoy": ["python", "../my_codeless-main/decoy_script.py"],
    }

    if command not in command_map:
        return "<pre style='color:red'>Unknown command.</pre>"

    try:
        if command == "run_project":
            subprocess.Popen(
                command_map[command],
                cwd=PROJECT_CWD,
                env=build_child_env(),
            )
            return "<pre>Started project in background.</pre>"

        output = subprocess.check_output(
            command_map[command],
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_CWD,
            env=build_child_env(),
        )
        return f"<pre>{output}</pre>"

    except subprocess.CalledProcessError as e:
        return f"<pre style='color:red'>{e.output}</pre>"


# ---------- NEW: Brand & style-variant panel actions ----------

@app.route("/brands/add-brand", methods=["POST"])
def add_brand():
    brand_name = request.form.get("brand_name", "").strip()
    login_url = request.form.get("login_url", "").strip()
    logo_url = request.form.get("logo_url", "").strip()
    background_hex = request.form.get("background_hex", "").strip() or "#FFFFFF"
    background_image_url = request.form.get("background_image_url", "").strip() or None
    logo_bg = request.form.get("logo_background_color", "").strip() or "#FFFFFF"
    primary_colors_raw = request.form.get("primary_colors_hex", "").strip()
    notes_raw = request.form.get("brand_notes", "").strip()

    if not brand_name:
        flash("Brand name is required.")
        return redirect("/")

    try:
        brands = load_brands()
    except Exception as e:
        flash(f"Error loading brands_out.json: {e}")
        return redirect("/")

    # prevent duplicates
    for b in brands:
        if b.get("brand") == brand_name:
            flash(f"Brand '{brand_name}' already exists.")
            return redirect("/")

    primary_colors = [
        c.strip()
        for c in primary_colors_raw.split(",")
        if c.strip()
    ] or ["#000000"]

    brand = {
        "brand": brand_name,
        "login_url": login_url,
        "logo_url": logo_url,
        "background_hex": background_hex,
        "background_image_url": background_image_url,
        "logo_background_color": logo_bg,
        "primary_colors_hex": primary_colors,
    }

    if notes_raw:
        brand["notes"] = [line.strip() for line in notes_raw.splitlines() if line.strip()]

    brand["style_variants"] = []

    brands.append(brand)
    try:
        save_brands(brands)
        flash(f"Brand '{brand_name}' added.")
    except Exception as e:
        flash(f"Error saving brands_out.json: {e}")

    return redirect("/")


@app.route("/update-news", methods=["POST"])
def update_news():
    for key in ["NEWS_QUERY", "BAIT_TOPIC", "SITE_NAME"]:
        if key in request.form:
            update_config_variable(key, request.form.get(key, ""))

    flash("News settings updated (NEWS_QUERY, BAIT_TOPIC, SITE_NAME).")
    return redirect("/")


@app.route("/brands/add-variant", methods=["POST"])
def add_variant():
    brand_name = request.form.get("brand_name", "").strip()
    variant_name = request.form.get("variant_name", "").strip()
    layout = request.form.get("layout", "").strip() or "centered_card"
    background = request.form.get("background", "").strip() or "none"
    v_logo = request.form.get("variant_logo_url", "").strip() or None
    v_bg = request.form.get("variant_background_image_url", "").strip() or None
    v_example = request.form.get("variant_login_example_url", "").strip() or None
    notes_raw = request.form.get("variant_notes", "").strip()

    if not brand_name or not variant_name:
        flash("Brand and variant name are required.")
        return redirect("/")

    try:
        brands = load_brands()
    except Exception as e:
        flash(f"Error loading brands_out.json: {e}")
        return redirect("/")

    target = None
    for b in brands:
        if b.get("brand") == brand_name:
            target = b
            break

    if target is None:
        flash(f"Brand '{brand_name}' not found.")
        return redirect("/")

    variant = {
        "name": variant_name,
        "layout": layout,
        "background": background,
    }

    if v_logo:
        variant["variant_primary_logo_url"] = v_logo

    if v_bg:
        variant["variant_background_image_url"] = v_bg

    if v_example:
        variant["variant_login_example_url"] = v_example

    if notes_raw:
        variant["notes"] = [line.strip() for line in notes_raw.splitlines() if line.strip()]
    else:
        variant["notes"] = ["None"]

    target.setdefault("style_variants", []).append(variant)

    try:
        save_brands(brands)
        flash(f"Variant '{variant_name}' added to brand '{brand_name}'.")
    except Exception as e:
        flash(f"Error saving brands_out.json: {e}")

    return redirect("/")


if __name__ == "__main__":
    app.run(port=5001)
