import os
import re

OLD_FOLDER = "pages"
NEW_FOLDER = "page_components"
PROJECT_ROOT = "."  # Adjust if needed


def rename_folder():
    if os.path.isdir(OLD_FOLDER):
        os.rename(OLD_FOLDER, NEW_FOLDER)
        print(f"Renamed '{OLD_FOLDER}' → '{NEW_FOLDER}'")
    else:
        print(f"Folder '{OLD_FOLDER}' not found.")


def update_imports():
    pattern = re.compile(rf"\bfrom {OLD_FOLDER}(\.[\w_]+)? import\b")
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                new_content = content.replace(
                    f"from {OLD_FOLDER}", f"from {NEW_FOLDER}"
                )
                if content != new_content:
                    with open(path, "w") as f:
                        f.write(new_content)
                    print(f"Updated imports in {path}")


if __name__ == "__main__":
    rename_folder()
    update_imports()
