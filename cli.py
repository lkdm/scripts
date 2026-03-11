#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
# "typer",
# ]
# ///

# Typer: [documentation](https://typer.tiangolo.com/tutorial/)
import typer

app = typer.Typer(
    no_args_is_help=True
)

@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def bye(name: str):
    print(f"Bye {name}")

@app.command()
def pwd():
	# Get the app directory where we are running
	app_dir = typer.get_app_dir(APP_NAME)

if __name__ == "__main__":
    app()
