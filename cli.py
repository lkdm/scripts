#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
# "typer",
# ]
# ///

# Typer: [documentation](https://typer.tiangolo.com/tutorial/)
import typer
from typing import Annotated

# Path can be used for system paths
# from pathlib import Path

# Subprocess can be used to execute system commands
# import subprocess
# subprocess.run(
#  cmd: list[str],
#  capture_output: bool,
#  text: bool
# ) -> { returncode: Union[0, 1] }
# If run did not return 0 or 1, you should raise a RuntimeError


app = typer.Typer(
    no_args_is_help=True
)

@app.command()
def hello(name: str):
    print(f"Hello {name}")

@app.command()
def dangerous_action(
	force: Annotated[
        bool, typer.Option(prompt="Are you sure you want to perform a dangerous action?")
    ],
):
	print(f"Danger")


@app.command()
def bye(name: str):
    print(f"Bye {name}")

@app.command()
def pwd():
	# Get the app directory where we are running
	app_dir = typer.get_app_dir(APP_NAME)

if __name__ == "__main__":
    app()
