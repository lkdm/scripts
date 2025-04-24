#!/usr/bin/env bash

# Minitol CLI tool

# Returns the ID for the Dev Container
get_minitol_container_id() {
    docker ps -q --filter name=minitol-app
}

# Attempts to execute a script on the Docker container, given an ID, subcommand, and arguments
_execute_sh() {
    if [ $# -lt 2 ]; then
        echo "Error: Insufficient arguments. Usage: _execute_sh <container_id> <command> [args...]" >&2
        return 1
    fi

    local container_id="$1"
    shift
    local command="$1"
    shift
    local args="$@"

    if ! docker ps -q --filter "id=$container_id" | grep -q .; then
        echo "Error: No running container found with ID ${container_id}." >&2
        return 1
    fi

    echo "Found container with ID ${container_id}. Attempting to run command..."
    docker exec -it "$container_id" bash -c "$command $args"
}

_git_worktree() {
    git rev-parse --show-toplevel 2>/dev/null
}

# Executes the input as SQL
execute_sql_in_container() {
    if [ -z "$MINITOL_DB_PASSWORD" ]; then
        echo "Error: MINITOL_DB_PASSWORD environment variable is not set."
        return 1
    fi

    container_id=$(docker ps -q --filter name=minitol-mariadb)
    if [ -n "$container_id" ]; then
        echo "Found MariaDB container with ID ${container_id}. Executing command..."

        # Join all arguments into a single command
        command="$*"

        # Execute the MySQL command and print the output
        docker exec -it "$container_id" bash -c "
            mysql -p'$MINITOL_DB_PASSWORD' -e \"$command\"
        "
    else
        echo "No running container found."
    fi
}

# Opens the MySQL shell
open_sql_repl_in_container() {
    if [ -z "$MINITOL_DB_PASSWORD" ]; then
        echo "Error: MINITOL_DB_PASSWORD environment variable is not set."
        return 1
    fi
    cid=$(docker ps -q --filter name=minitol-mariadb)
    _execute_sh $cid mysql -p'$MINITOL_DB_PASSWORD'
}


open_minitol_shell() {
    local cid=$(get_minitol_container_id)

    if [ -z "$cid" ]; then
        echo "Error: No running Minitol container found." >&2
        return 1
    fi

    if [ $# -eq 0 ]; then
        # No arguments provided, open zsh shell
        _execute_sh "$cid" "zsh"
    else
        # Command and arguments provided, execute them
        local command="$1"
        shift
        local args="$@"
        _execute_sh "$cid" "$command" "$args"
    fi
}

# Starts Docker Engine then starts the dev app in the container
start() {
    worktree=$(_git_worktree)
    if [ "$worktree" == "" ]; then
        echo "Must execute this script from a valid git worktree"
        exit 1
    fi
    echo "Using worktree: $worktree"

	nohup docker compose -p minitol -f "$(_git_worktree)/.devcontainer/docker-compose.yml" up -d > /tmp/minitol.log 2>&1 </dev/null &
	sleep 0.5
	container_id=$(get_minitol_container_id)
    if [ -n "$container_id" ]; then
        echo "Started container with ID ${container_id}. Attempting to run..."
        # Keep track of which worktree the container was initialised from
        docker exec -it "$container_id" bash -c "
            echo '$worktree' > /tmp/worktree
        "
        # Start the minotol server
        docker exec -it "$container_id" bash -c "
        	start
        "
        echo "Logs are available by running:
mt log"
    else
        echo "Could not start container."
    fi
}

which_worktree() {
    cid=$(get_minitol_container_id)
    docker exec "$cid" cat /tmp/worktree 2>/dev/null || echo "No worktree information stored"
}


logs() {
    local log_file="/tmp/minitol.log"

    if [[ "$1" == "--watch" ]]; then
        echo "Watching logs..."
        tail -f "$log_file"
    elif [[ "$1" == "--tail" ]]; then
        echo "Displaying last 10 lines of logs..."
        tail "$log_file"
    else
        echo "Paging logs (default)..."
        less "$log_file"  # Default to less
    fi
}

help() {
	echo "mt is a comprehensive suite of tools to streamline Minitol development on POSIX-based systems (Linux, macOS).

Usage: mt <subcommand> [options]

AVAILABLE SUBCOMMANDS

development environment
    start                     Launch Docker engine and initialise the dev environment
    which                     Output the git worktree the start subcommand was executed from.
    sh                        Access a ZSH shell within the dev container or run a command
    sh <subcmd> [<arg1>, ...] Execute a specified command with optional arguments in the container's shell
    id                        Get the dev container's ID

database operations
    sql                       Execute a SQL script on the dev database
    slq \"<sh>\"              Launch an interactive SQL shell connected to the dev database

general
    help                      Display this help message

EXAMPLES

    mt start
    mt sql 'SELECT * FROM table LIMIT 1;'
    mt sh \"cat ~/README.md\" | less

Ensure Docker engine is installed and properly configured on your system before using this tool.
See: https://docs.docker.com/engine/install/
	"
}
# Main script logic
if [ $# -eq 0 ]; then
    help
    exit 1
fi


subcommand="$1"
shift

case "$subcommand" in
    id)
        get_minitol_container_id "$@"
        ;;
    sql)
        execute_sql_in_container "$@"
        ;;
    sh)
        open_minitol_shell "$@"
        ;;
    which)
        which_worktree "$@"
        ;;
    start)
        start "$@"
        ;;
    help)
    	help "$@"
    	;;
    *)
        echo "mt: $subcommand is not a subcommand. See: mt help"
        exit 1
        ;;
esac
