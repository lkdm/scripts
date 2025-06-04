// Install:
//
//   cargo install --git https://github.com/lkdm/scripts mt
//
// Usage:
//
//   mt
//   mt sh
//

use clap::{Parser, Subcommand};
use rpassword::prompt_password;
use std::{
    path::{Path, PathBuf},
    process::{Command, Stdio},
    thread,
    time::Duration,
};
use thiserror::Error;

#[derive(Debug, Error)]
enum CliError {
    #[error("JSON parse error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("Command execution failed: {0}")]
    Command(#[from] std::io::Error),
    #[error("Invalid UTF-8 output: {0}")]
    InvalidUtf8(#[from] std::string::FromUtf8Error),
    #[error("No output from command")]
    EmptyOutput,
    #[error("Git error: {0}")]
    Git(String),
    #[error("Docker error: {0}")]
    Docker(String),
    #[error("Configuration error: {0}")]
    Config(String),
}

type Result<T> = std::result::Result<T, CliError>;

trait CommandExt {
    fn execute_interactive(&mut self) -> Result<()>;
    fn execute_capture(&mut self) -> Result<String>;
}

impl CommandExt for Command {
    fn execute_interactive(&mut self) -> Result<()> {
        let status = self
            .stdin(Stdio::inherit())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .status()
            .map_err(|e| CliError::Command(e))?;

        if !status.success() {
            return Err(CliError::Command(std::io::Error::new(
                std::io::ErrorKind::Other,
                format!("Command failed with exit code: {}", status),
            )));
        }
        Ok(())
    }

    fn execute_capture(&mut self) -> Result<String> {
        let output = self.output().map_err(CliError::Command)?;

        if !output.status.success() {
            return Err(CliError::Command(std::io::Error::new(
                std::io::ErrorKind::Other,
                format!("Command failed with exit code: {}", output.status),
            )));
        }

        if output.stdout.is_empty() {
            return Err(CliError::EmptyOutput);
        }

        String::from_utf8(output.stdout).map_err(CliError::InvalidUtf8)
    }
}

fn sh(command: &str) -> Result<()> {
    Command::new("bash")
        .arg("-c")
        .arg(command)
        .execute_interactive()
}

fn dexec(container_id: &str, command: &str) -> Result<()> {
    Command::new("docker")
        .args(["exec", "-it", container_id, "bash", "-c", command])
        .execute_interactive()
}

fn sh_capture(command: &str) -> Result<String> {
    Command::new("bash")
        .arg("-c")
        .arg(command)
        .execute_capture()
}

fn dexec_capture(container_id: &str, command: &str) -> Result<String> {
    Command::new("docker")
        .args(["exec", container_id, "bash", "-c", command])
        .execute_capture()
}

fn get_container_id(name: &str) -> Result<String> {
    let output = Command::new("docker")
        .args(["ps", "-q", "--filter", &format!("name={}", name)])
        .output()
        .map_err(|e| CliError::Docker(format!("Failed to execute docker ps: {}", e)))?;

    if !output.status.success() {
        return Err(CliError::Docker(format!(
            "docker ps failed with exit code: {}",
            output.status
        )));
    }

    let id = String::from_utf8(output.stdout)
        .map_err(|e| CliError::Docker(format!("Invalid UTF-8 from docker: {}", e)))?
        .trim()
        .to_string();

    if id.is_empty() {
        return Err(CliError::EmptyOutput);
    }

    Ok(id)
}

fn git_worktree_path() -> Result<PathBuf> {
    let output = Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()
        .map_err(|e| CliError::Git(format!("Failed to execute git rev-parse: {}", e)))?;

    if !output.status.success() {
        return Err(CliError::Git(format!(
            "git rev-parse failed with exit code: {}",
            output.status
        )));
    }

    let path = String::from_utf8(output.stdout)
        .map_err(|e| CliError::Git(format!("Invalid UTF-8 from git: {}", e)))?
        .trim()
        .to_string();

    if path.is_empty() {
        return Err(CliError::Git("No git worktree found".to_string()));
    }

    Ok(PathBuf::from(path))
}

/// Attempt to use docker-compose.override.yml
fn preferred_compose_paths(worktree_path: &Path) -> Vec<PathBuf> {
    let base = worktree_path.join(".devcontainer/docker-compose.yml");
    let override1 = worktree_path.join(".devcontainer/docker-compose.override.yml");
    let override2 = dirs::home_dir().map(|h| h.join(".tolconfig/docker-compose.override.yml"));

    let mut files = vec![base.clone()];
    if override1.exists() {
        files.push(override1.clone());
        println!(
            "\x1b[33m⚠️  Using ./.devcontainer/docker-compose.override.yml as an override.\n\tBase: ./.devcontainer/docker-compose.yml\x1b[0m"
        );
    }
    if let Some(ref override2_path) = override2 {
        if override2_path.exists() {
            files.push(override2_path.clone());
            println!(
                "\x1b[33m⚠️  Using ~/.tolconfig/docker-compose.override.yml as an additional override.\x1b[0m"
            );
        }
    }
    if files.len() == 1 {
        println!(
            "\x1b[33m⚠️  Using base ./.devcontainer/docker-compose.yml (no overrides found).\x1b[0m"
        );
    }
    std::thread::sleep(std::time::Duration::from_secs(1));
    files
}

fn up(worktree_path: &Path) -> Result<String> {
    let compose_paths = preferred_compose_paths(worktree_path);

    // Existence check
    for path in &compose_paths {
        if !path.exists() {
            return Err(CliError::Docker(format!(
                "Compose file not found at: {}",
                path.display()
            )));
        }
    }

    // Collect file paths as Strings
    let file_strings: Vec<String> = compose_paths
        .iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect();

    // Build args
    let mut args = vec!["compose", "-p", "minitol"];
    for file in &file_strings {
        args.push("-f");
        args.push(file);
    }
    args.extend(&["up", "-d"]);

    let output = Command::new("docker")
        .args(&args)
        .stdout(Stdio::inherit())
        .status()
        .map_err(|e| CliError::Docker(format!("Failed to execute docker compose up: {}", e)))?;

    let container_id = get_container_id("minitol-app")?;
    dexec(
        &container_id,
        &format!(
            "echo '{}' > /tmp/worktree",
            compose_paths.last().unwrap().to_string_lossy()
        ),
    )?;
    Ok(container_id)
}

fn down(worktree_path: &Path) -> Result<()> {
    let compose_paths = preferred_compose_paths(worktree_path);

    // Existence check
    for path in &compose_paths {
        if !path.exists() {
            return Err(CliError::Docker(format!(
                "Compose file not found at: {}",
                path.display()
            )));
        }
    }

    // Collect file paths as Strings
    let file_strings: Vec<String> = compose_paths
        .iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect();

    // Build args with all -f flags
    let mut args = vec!["compose", "-p", "minitol"];
    for file in &file_strings {
        args.push("-f");
        args.push(file);
    }
    args.push("down");

    Command::new("docker")
        .args(&args)
        .status()
        .map_err(|e| CliError::Docker(format!("Failed to execute docker compose down: {}", e)))?;

    Ok(())
}

// fn build(worktree_path: &PathBuf) -> Result<()> {
//     let abs_path = preferred_compose_paths(worktree_path);
//     let abs_path_str = abs_path.to_string_lossy();
//     //
//     // Command::new("docker")
//     //     .args([
//     //         "compose",
//     //         "-p",
//     //         "minitol",
//     //         "-f",
//     //         &abs_path_str,
//     //         "build",
//     //         "--no-cache",
//     //     ])
//     //     .execute_interactive()
// }

fn run_lifecycle_commands(container_id: &str, devcontainer_path: &PathBuf) -> Result<()> {
    let config_path = devcontainer_path.join("devcontainer.json");
    let config = std::fs::read_to_string(&config_path)
        .map_err(|e| CliError::Docker(format!("Failed to read devcontainer.json: {}", e)))?;

    let config: serde_json::Value = serde_json::from_str(&config)
        .map_err(|e| CliError::Docker(format!("Invalid devcontainer.json: {}", e)))?;

    // Post-create command
    if let Some(cmd) = config["postCreateCommand"].as_str() {
        dexec(container_id, cmd)?;
    }

    // Post-start command (runs on every start)
    if let Some(cmd) = config["postStartCommand"].as_str() {
        dexec(container_id, cmd)?;
    }

    Ok(())
}

#[derive(clap::Parser)]
#[command(
    author,
    version,
    about,
    long_about = None,
    after_help = concat!(
        "\x1b[1;4mExamples\x1b[0m:\n",
        "  mt start\n",
        "  mt sh\n",
        "  mt sh strict\n",
        "  mt sh unstrict\n",
        "  mt sh dbclone db1 db2\n",
        "  mt sql\n",
        "  mt sql SELECT 1\n",
        "\n",
        "\n",
        "\x1b[1;4mConfiguring Minitol\x1b[0m:\n",
        "This tool automatically applies Docker Compose overrides in the following order:\n",
        "  1. /path/to/repo/.devcontainer/docker-compose.yml (base)\n",
        "  2. /path/to/repo/.devcontainer/docker-compose.override.yml (if present)\n",
        "  3. ~/.tolconfig/docker-compose.override.yml (if present)\n",
        "Later files override earlier ones. Missing files are skipped.\n"
    )
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    #[command(about = "Launch the containerised development environment")]
    Start {
        #[arg(help = "Path to git worktree containing developer environment")]
        path: Option<PathBuf>,
    },
    #[command(about = "Stop the containerised development environment")]
    Stop,
    #[command(about = "Run an interactive shell within the development container")]
    Sh {
        #[arg(
            trailing_var_arg = true,
            allow_hyphen_values = true,
            help = "Command to execute in the container"
        )]
        command: Vec<String>,
    },
    // #[command(about = "Execute a local file as a script in the development container")]
    // Exec {
    //     #[arg()]
    //     path: PathBuf,
    // },
    #[command(about = "Run a SQL command")]
    SQL {
        #[arg(
            trailing_var_arg = true,
            allow_hyphen_values = true,
            help = "Query to execute in the database"
        )]
        query: Vec<String>,

        #[arg(short, long)]
        user: Option<String>,

        #[arg(short, long)]
        password: Option<String>,
    },
    #[command(about = "View start script logs")]
    Logs,
    #[command(about = "Outputs information about the running development containers")]
    Info,
    // #[command(about = "Rebuilds the development container")]
    // Rebuild,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start { path } => {
            let resolved_path = match path {
                Some(p) => p,
                None => &git_worktree_path()?,
            };
            let container_id = up(&resolved_path)?;
            dexec(&container_id, "start | tee /tmp/mt")?;
        }
        Commands::Stop => {
            let container_id = get_container_id("minitol-app")?;
            dexec(&container_id, "stop")?;
        }
        Commands::Sh { command } => {
            let container_id = get_container_id("minitol-app")?;
            let command_string = if command.is_empty() {
                "zsh".to_string()
            } else {
                command.join(" ")
            };
            dexec(&container_id, &command_string)?;
        }
        Commands::SQL {
            query,
            user,
            password,
        } => {
            let container_id = get_container_id("minitol-mariadb")?;

            let password = match password {
                Some(p) => p.clone(),
                None => prompt_password("Database password: ")?,
            };

            let user = user.as_deref().unwrap_or("root");

            let mysql_cmd = if query.is_empty() {
                format!("mysql -u{} -p'{}'", user, password)
            } else {
                format!(
                    "mysql -u{} -p'{}' -e \"{}\"",
                    user,
                    password,
                    query.join(" ")
                )
            };

            dexec(&container_id, &mysql_cmd)?;
        }
        Commands::Logs => {
            let container_id = get_container_id("minitol-app")?;
            dexec(&container_id, "tail -f /tmp/mt")?;
        }
        Commands::Info => {
            let container_id = get_container_id("minitol-app")?;

            println!("Container ID: {}", container_id);

            let worktree = dexec_capture(&container_id, "cat /tmp/worktree 2>/dev/null")?;

            println!("Worktree Path: {}", worktree.trim());
        } // Commands::Exec { path } => {
          //     let container_id = get_container_id("minitol-app");
          //     todo!("Execute path");
          // }

          // Commands::Rebuild => {
          //     let path = git_worktree_path()?;
          //
          //     // 1. Stop and remove existing containers
          //     down(&path)?;
          //
          //     // 2. Rebuild with fresh images
          //     build(&path)?;
          //
          //     // 3. Start new containers
          //     let container_id = up(&path)?;
          //
          //     // 4. Execute lifecycle commands
          //     let devcontainer_path = path.join(".devcontainer");
          //     run_lifecycle_commands(&container_id, &devcontainer_path)?;
          //
          //     println!("Rebuild complete. New container ID: {}", container_id);
          // }
    }
    Ok(())
}
