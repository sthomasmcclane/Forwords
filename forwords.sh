#!/bin/bash

###################################################################
# Forwords: A Simple Writing App Script
# 
# Forwords is a simple Bash script designed to help you focus on writing
# by providing a clean interface and tracking your word count.
# It offers inspirational banners, notes, and style prompts to get your
# creative juices flowing.
###################################################################

# Default values (these are only used if they are not found in a .forwords.config file)
DEFAULT_SAVE_FILE="manuscript.txt"
DEFAULT_BANNER_COLOR="blue"
DEFAULT_BANNER_TYPE="Quote"

# Default Forwords directory structure
DEFAULT_FORWORDS_DIR="$HOME/Forwords"
DEFAULT_MANUSCRIPTS_DIR="$DEFAULT_FORWORDS_DIR/Manuscripts"
DEFAULT_RESOURCES_DIR="$DEFAULT_FORWORDS_DIR/Resources"

# ANSI color codes
COLOR_BLUE="\e[94m"
COLOR_RED="\e[91m"
COLOR_GREEN="\e[92m"
COLOR_YELLOW="\e[93m"
COLOR_MAGENTA="\e[95m"
COLOR_CYAN="\e[96m"
COLOR_WHITE="\e[97m"
COLOR_RESET="\e[0m"

# Set defaults
SAVE_FILE="$DEFAULT_SAVE_FILE"
BANNER_COLOR_NAME="$DEFAULT_BANNER_COLOR"
DEFAULT_BANNER="$DEFAULT_BANNER_TYPE"

# Load config from ~/Forwords/.forwords.config if it exists
CONFIG_FILE="$DEFAULT_FORWORDS_DIR/.forwords.config"
if [[ -f "$CONFIG_FILE" ]]; then
    while IFS=':' read -r key value; do
        # Remove whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        case "$key" in
            SAVE_FILE) SAVE_FILE="$value" ;;
            BANNER_COLOR) BANNER_COLOR_NAME="$value" ;;
            DEFAULT_BANNER) DEFAULT_BANNER="$value" ;;
        esac
    done < "$CONFIG_FILE"
else
    # Create default config file if it doesn't exist
    create_default_config
fi

# Parse SAVE_FILE to determine save directory and create structure
parse_save_path() {
    local save_path="$1"
    
    # Expand user home directory
    save_path="${save_path/#\~/$HOME}"
    
    if [[ "$save_path" = /* ]]; then
        # Absolute path - use as specified
        SAVE_DIR="$(dirname "$save_path")"
        MANUSCRIPT_NAME="$(basename "$save_path" .txt)"
    else
        # Relative path - use default Forwords structure
        SAVE_DIR="$DEFAULT_MANUSCRIPTS_DIR"
        MANUSCRIPT_NAME="${save_path%.txt}"
    fi
    
    # Ensure the save directory exists
    mkdir -p "$SAVE_DIR" || { echo "Error: Cannot create directory $SAVE_DIR"; exit 1; }
    
    # Set the full save file path
    SAVE_FILE_FULL="$SAVE_DIR/${MANUSCRIPT_NAME}.txt"
}

# Parse the save path
parse_save_path "$SAVE_FILE"

# Map color name to ANSI code (case-insensitive)
case "${BANNER_COLOR_NAME,,}" in
    blue)   BANNER_COLOR="$COLOR_BLUE" ;;
    red)    BANNER_COLOR="$COLOR_RED" ;;
    green)  BANNER_COLOR="$COLOR_GREEN" ;;
    yellow) BANNER_COLOR="$COLOR_YELLOW" ;;
    magenta) BANNER_COLOR="$COLOR_MAGENTA" ;;
    cyan)   BANNER_COLOR="$COLOR_CYAN" ;;
    white)  BANNER_COLOR="$COLOR_WHITE" ;;
    *)      BANNER_COLOR="$COLOR_BLUE" ;;
esac

###################################################################
# Some files are excluded from git commits in the .gitignore file #
# Check this file and adjust accordingly if you plan to add new   #
# files or you want to commit the files that this script uses.    #
###################################################################

# Get the absolute path of the script, even if it's invoked via a symlink
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"

# Construct paths relative to the script's directory
RESOURCE_DIR="$SCRIPT_DIR/resources"

# Create default Forwords directory structure if using default paths
if [[ "$SAVE_DIR" == "$DEFAULT_MANUSCRIPTS_DIR" ]]; then
    mkdir -p "$DEFAULT_FORWORDS_DIR" || { echo "Error: Cannot create $DEFAULT_FORWORDS_DIR"; exit 1; }
    mkdir -p "$DEFAULT_MANUSCRIPTS_DIR" || { echo "Error: Cannot create $DEFAULT_MANUSCRIPTS_DIR"; exit 1; }
    mkdir -p "$DEFAULT_RESOURCES_DIR" || { echo "Error: Cannot create $DEFAULT_RESOURCES_DIR"; exit 1; }
fi

# Create work directory and output file if they don't exist
touch "$SAVE_FILE_FULL" || { echo "Error: Cannot create $SAVE_FILE_FULL"; exit 1; }

# Determine banner based on DEFAULT_BANNER setting from config
case "${DEFAULT_BANNER,,}" in
    quote)
        # Check both default Forwords resources and app resources
        quotes_file="$DEFAULT_RESOURCES_DIR/quotes.txt"
        if [[ ! -f "$quotes_file" ]]; then
            quotes_file="$RESOURCE_DIR/quotes.txt"
        fi
        
        if [[ -f "$quotes_file" ]]; then
            banner_file="$quotes_file"
        else
            echo "No quotes file found. Create $DEFAULT_RESOURCES_DIR/quotes.txt with your favorite writing quotes (one per line)."
            echo "No banner available."
            banner_file=""
        fi
        ;;
    note)
        # Check for note.txt file
        note_file="$DEFAULT_RESOURCES_DIR/note.txt"
        if [[ -f "$note_file" ]]; then
            banner_file="$note_file"
        else
            echo "No note file found. Create $DEFAULT_RESOURCES_DIR/note.txt with your custom message."
            echo "No banner available."
            banner_file=""
        fi
        ;;
    prompt)
        # Generate a new random writing prompt using shared config
        STYLE_PROMPT=$(generate_style_prompt)
        # Write to a temp file for compatibility with rest of script
        style_file="$DEFAULT_RESOURCES_DIR/style.txt"
        echo "$STYLE_PROMPT" > "$style_file"
        banner_file="$style_file"
        ;;
    *)
        echo "Unknown banner type: $DEFAULT_BANNER"
        echo "Valid options: Quote, Note, Prompt"
        echo "No banner available."
        banner_file=""
        ;;
esac

# Ensure banner_file is not empty before trying to read from it
if [[ -s "$banner_file" ]]; then
  BANNER=$(sort -R "$banner_file" | head -n 1)
else
  BANNER="No banner available."
fi

# Initialize word counts (AFTER creating the file)
STARTING_WORD_COUNT=$(wc -w "$SAVE_FILE_FULL" | cut -f1 -d ' ')
SESSION_WORD_COUNT=0
TOTAL_WORD_COUNT=$STARTING_WORD_COUNT

# Function to update word counts
update_word_counts() {
    SENTENCE_WORD_COUNT=$(echo "$1" | wc -w)
    TOTAL_WORD_COUNT=$(wc -w "$SAVE_FILE_FULL" | cut -f1 -d ' ')
    SESSION_WORD_COUNT=$((TOTAL_WORD_COUNT - STARTING_WORD_COUNT))
}

# Function to create default config file
create_default_config() {
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
    EXAMPLE_FILE="$SCRIPT_DIR/docs/forwords.config.example"
    
    if [[ -f "$EXAMPLE_FILE" ]]; then
        # Create Forwords directory if it doesn't exist
        mkdir -p "$DEFAULT_FORWORDS_DIR" || { echo "Error: Cannot create $DEFAULT_FORWORDS_DIR"; exit 1; }
        
        # Copy the example file
        cp "$EXAMPLE_FILE" "$CONFIG_FILE" || { echo "Error: Cannot copy example config"; exit 1; }
        echo "Created default config file: $CONFIG_FILE"
        echo "Using default settings. Edit $CONFIG_FILE to customize."
    else
        echo "Warning: Example config file not found. Using hardcoded defaults."
    fi
}

# Function to generate style prompt using shared config
generate_style_prompt() {
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
    PROMPTS_FILE="$SCRIPT_DIR/config/prompts.txt"
    
    if [[ -f "$PROMPTS_FILE" ]]; then
        # Load prompt components from shared config
        while IFS='=' read -r category items; do
            # Skip comments and empty lines
            [[ "$category" =~ ^#.*$ || -z "$category" ]] && continue
            # Remove whitespace and store in variables
            category=$(echo "$category" | xargs)
            items=$(echo "$items" | xargs)
            
            case "$category" in
                VOICE) voicelist=(${items//,/ }) ;;
                TONE) tonelist=(${items//,/ }) ;;
                TENSE) tenselist=(${items//,/ }) ;;
                POV) povlist=(${items//,/ }) ;;
                PACE) pacelist=(${items//,/ }) ;;
                GENRE) genrelist=(${items//,/ }) ;;
                SETTING) settinglist=(${items//,/ }) ;;
            esac
        done < "$PROMPTS_FILE"
    else
        # Fallback to hardcoded values if shared config not found
        voicelist=("formal" "informal" "conversational" "professional" "academic" "playful" "sarcastic" "intimate" "detached" "poetic" "technical" "colloquial" "elegant" "rough" "smooth" "direct" "evasive")
        tonelist=("light-hearted" "serious" "dark" "humorous" "whimsical" "melancholic" "uplifting" "suspenseful" "nostalgic" "mysterious" "romantic" "cynical" "optimistic" "pessimistic" "neutral" "dramatic" "understated" "intense" "gentle" "aggressive")
        tenselist=("past" "present" "future" "conditional" "imperative")
        povlist=("first-person" "second-person" "third-person (limited)" "third-person (omniscient)" "third-person (objective)" "multiple perspectives" "unreliable narrator")
        pacelist=("fast" "slow" "steadily" "frenetically" "rhythmically" "haltingly" "smoothly" "chaotically" "methodically" "sporadically")
        genrelist=("mystery" "romance" "science fiction" "fantasy" "historical" "contemporary" "thriller" "comedy" "drama" "horror" "western" "adventure" "literary" "young adult" "children's" "erotica")
        settinglist=("urban" "rural" "suburban" "desert" "forest" "mountain" "coastal" "arctic" "tropical" "space" "underwater" "underground" "post-apocalyptic" "medieval" "futuristic" "alternate history")
    fi
    
    # Generate random selections
    selectedvoice=${voicelist[$RANDOM % ${#voicelist[@]} ]}
    selectedtone=${tonelist[$RANDOM % ${#tonelist[@]} ]}
    selectedpace=${pacelist[$RANDOM % ${#pacelist[@]} ]}
    selectedpov=${povlist[$RANDOM % ${#povlist[@]} ]}
    selectedtense=${tenselist[$RANDOM % ${#tenselist[@]} ]}
    selectedgenre=${genrelist[$RANDOM % ${#genrelist[@]} ]}
    selectedsetting=${settinglist[$RANDOM % ${#settinglist[@]} ]}
    
    echo "Write a $selectedtone $selectedgenre story set in a $selectedsetting environment. Use a $selectedvoice voice with $selectedpace pacing in $selectedtense-tense from a $selectedpov perspective."
}

trap 'exit' INT  # Terminate the script with Ctrl-C

while true; do
    clear

    # Display the banner (if it's set)
    if [[ -n "$BANNER" ]]; then  # Check if $BANNER is not empty
        printf "${BANNER_COLOR}%s${COLOR_RESET}\n" "$BANNER"
    fi

    # Display the last sentence from the save file (if it's not empty)
    if [[ -s "$SAVE_FILE_FULL" ]]; then
        LAST_SENTENCE=$(tail -n 1 "$SAVE_FILE_FULL")
        echo "$LAST_SENTENCE"
    fi

    read -p "[$(printf "%d" $SESSION_WORD_COUNT)/$(printf "%d" $TOTAL_WORD_COUNT)]: " NEW_SENTENCE

    # Append new sentence (or blank line) to the save file
	echo "$NEW_SENTENCE" >> "$SAVE_FILE_FULL"

    update_word_counts "$NEW_SENTENCE"
done
