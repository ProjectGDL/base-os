# System-wide Oh My Zsh (read-only, no auto-updates) - Project GDL OS

export ZSH=/usr/share/oh-my-zsh

ZSH_THEME="fishy"

zstyle ':omz:update' mode disabled

plugins=(git zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh
