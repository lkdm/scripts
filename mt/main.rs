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
    path::PathBuf,
    process::{Command, Stdio},
};
use thiserror::Error;

#[derive(Debug, Error)]
enum CliError {
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

fn up(worktree_path: &PathBuf) -> Result<String> {
    let abs_path = worktree_path.join(".devcontainer/docker-compose.yml");
    let abs_path_str = abs_path.to_string_lossy();

    let output = Command::new("docker")
        .args(["compose", "-p", "minitol", "-f", &abs_path_str, "up", "-d"])
        .output()
        .map_err(|e| CliError::Docker(format!("Failed to execute docker compose up: {}", e)))?;

    if !output.status.success() {
        eprintln!(
            "Docker compose up failed:\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
        return Err(CliError::Docker(format!(
            "docker compose up failed with exit code: {}",
            output.status
        )));
    }

    let container_id = get_container_id("minitol-app")?;
    dexec_capture(
        &container_id,
        &format!("echo '{}' > /tmp/worktree", &abs_path_str),
    )?;
    Ok(container_id)
}

#[derive(Parser)]
#[command(author, version, about, long_about = None,
	after_help=r#"EXAMPLES:
    mt sh strict
    mt sh unstrict
    mt dbclone db1 db2
"#
	)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    #[command(about = "Launch the containerised development environment")]
    Start,
    #[command(about = "Run an interactive shell within the development container")]
    Sh {
        #[arg(
            trailing_var_arg = true,
            allow_hyphen_values = true,
            help = "Command to execute in the container"
        )]
        command: Vec<String>,
    },
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
    #[command(about = "Outputs information about the running development containers")]
    Info,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start => {
            let path = git_worktree_path()?;
            let container_id = up(&path)?;
            dexec(&container_id, "start")?;
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

        Commands::Info => {
            let container_id = get_container_id("minitol-app")?;

            println!("Container ID: {}", container_id);

            let worktree = dexec_capture(&container_id, "cat /tmp/worktree 2>/dev/null")?;

            println!("Worktree Path: {}", worktree.trim());
        }
    }
    Ok(())
}
