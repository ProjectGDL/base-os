# Add user-local binaries to PATH - Project GDL OS
[[ -d "$HOME/.local/bin" ]] && path=("$HOME/.local/bin" $path)
typeset -U path
