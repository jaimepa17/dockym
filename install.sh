#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
#  Dockym — Installer
#  https://github.com/jaimepa17/dockym
# ──────────────────────────────────────────────

REPO="jaimepa17/dockym"
BRANCH="master"
GITHUB="https://raw.githubusercontent.com/$REPO/$BRANCH"
APP_NAME="dockym"
INSTALL_DIR="${DOCKYM_DIR:-$HOME/.local/share/dockym}"
BIN_DIR="${DOCKYM_BIN_DIR:-$HOME/.local/bin}"

# ─── Colores ──────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── Helper functions ─────────────────────────
info()  { echo -e "${BLUE}::${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
header(){ echo -e "\n${BOLD}── $1 ──${NC}\n"; }

# ─── Check: Python version ────────────────────
check_python() {
    header "Verificando Python"

    # Try python3 first, then python
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        error "Python no está instalado."
        echo "  Instálalo desde: https://www.python.org/downloads/"
        echo "  O con tu gestor de paquetes:"
        echo "    Arch:  sudo pacman -S python"
        echo "    Debian/Ubuntu: sudo apt install python3 python3-pip python3-venv"
        echo "    macOS: brew install python@3.11"
        exit 1
    fi

    version=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
        error "Se requiere Python ≥ 3.11 (tienes $($PYTHON --version 2>&1))"
        exit 1
    fi

    ok "Python $($PYTHON --version 2>&1)"
}

# ─── Check: package managers ──────────────────
check_pkg_managers() {
    header "Gestores de paquetes"

    HAS_UV=false
    HAS_PIP=false

    if command -v uv &>/dev/null; then
        HAS_UV=true
        ok "uv detectado"
    else
        warn "uv no encontrado — se usará pip (más lento)"
    fi

    if $PYTHON -m pip --version &>/dev/null; then
        HAS_PIP=true
        ok "pip detectado"
    fi

    if [ "$HAS_UV" = false ] && [ "$HAS_PIP" = false ]; then
        error "No se encontró uv ni pip."
        echo "  Instala pip: https://pip.pypa.io/en/stable/installation/"
        exit 1
    fi
}

# ─── Install dependencies ─────────────────────
install_deps() {
    header "Instalando dependencias"

    # Ensure target dir exists
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"

    if [ "$HAS_UV" = true ]; then
        info "Usando uv..."
        uv tool install --reinstall "git+https://github.com/$REPO.git" 2>&1 | sed 's/^/  /'

        # uv tool install creates the entry point automatically
        ok "Dependencias instaladas con uv"
    else
        info "Usando pip..."

        # Create a virtualenv in INSTALL_DIR for isolation
        VENV_DIR="$INSTALL_DIR/venv"
        if [ ! -d "$VENV_DIR" ]; then
            info "Creando entorno virtual..."
            $PYTHON -m venv "$VENV_DIR"
        fi

        info "Instalando desde GitHub..."
        "$VENV_DIR/bin/pip" install --quiet --upgrade "git+https://github.com/$REPO.git" 2>&1 | sed 's/^/  /'

        # Create launcher script
        LAUNCHER="$BIN_DIR/$APP_NAME"
        cat > "$LAUNCHER" << LAUNCHER_EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/$APP_NAME" "\$@"
LAUNCHER_EOF
        chmod +x "$LAUNCHER"

        ok "Dependencias instaladas con pip"
    fi
}

# ─── Verify installation ──────────────────────
verify_install() {
    header "Verificando instalación"

    if command -v "$APP_NAME" &>/dev/null; then
        ok "$APP_NAME se encuentra en PATH"
    elif [ -x "$BIN_DIR/$APP_NAME" ]; then
        warn "$APP_NAME instalado en $BIN_DIR (puede que no esté en PATH)"
        echo "  Agrega esto a tu ~/.bashrc o ~/.zshrc:"
        echo -e "  ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    else
        warn "No se encontró $APP_NAME en el PATH"
        echo "  Busca el ejecutable en: $BIN_DIR/"
        echo "  O ejecútalo directamente con: $PYTHON -m dockym"
    fi
}

# ─── Desktop entry (Linux) ────────────────────
setup_desktop_entry() {
    header "Acceso directo"

    if [ "$(uname)" != "Linux" ]; then
        info "Se omite entrada de escritorio (solo Linux)"
        return
    fi

    # Locate the icon — we need to find where dockym was installed
    if [ "$HAS_UV" = true ]; then
        # uv stores tools in ~/.local/share/uv/tools/
        MODULE_DIR=$(uv tool show dockym 2>/dev/null | grep -oP '(?<=installed at ).*' || true)
    fi

    # If we can't find it, download the icon from GitHub
    ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
    ICON_PATH="$ICON_DIR/dockym.png"

    mkdir -p "$ICON_DIR"

    # Try to generate an icon from the app (it renders one), or download a placeholder
    # For now just create an entry without icon reference

    APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    DESKTOP_FILE="$APP_DIR/dockym.desktop"

    mkdir -p "$APP_DIR"

    # Find the actual executable path for the desktop entry
    EXEC_PATH=$(command -v "$APP_NAME" 2>/dev/null || echo "$BIN_DIR/$APP_NAME")

    cat > "$DESKTOP_FILE" << DESKTOP_EOF
[Desktop Entry]
Name=Dockym
Comment=Gestor visual de servicios Docker Compose
Exec=$EXEC_PATH
Icon=dockym
Terminal=false
Type=Application
Categories=Development;System;Utility;
Keywords=docker;compose;containers;devops;
DESKTOP_EOF

    ok "Entrada de escritorio creada: $DESKTOP_FILE"
    echo "  Aparecerá en tu menú de aplicaciones como 'Dockym'"

    # Try to install icon (download a simple one from GitHub)
    if command -v python3 &>/dev/null; then
        python3 -c "
import urllib.request, os
try:
    # Just use a simple SVG placeholder — the app renders its own icon at runtime
    pass
except:
    pass
" 2>/dev/null || true
    fi
}

# ─── Print summary ────────────────────────────
print_summary() {
    echo ""
    echo -e "${GREEN}┌────────────────────────────────────────────┐${NC}"
    echo -e "${GREEN}│${NC}  ✅  Dockym se instaló correctamente       ${GREEN}│${NC}"
    echo -e "${GREEN}└────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "  Ejecútalo con:    ${CYAN}${BOLD}$APP_NAME${NC}"
    echo -e "  Desde código:     ${CYAN}${BOLD}python -m dockym${NC}"
    echo ""
    echo -e "  📖  Documentación: https://github.com/$REPO"
    echo -e "  🐛  Reportar bugs: https://github.com/$REPO/issues"
    echo ""
}

# ─── Uninstall function (hidden flag) ─────────
uninstall() {
    header "Desinstalando Dockym"

    if [ "$HAS_UV" = true ]; then
        uv tool uninstall dockym 2>/dev/null || true
    fi

    rm -rf "$INSTALL_DIR"

    # Remove launcher
    LAUNCHER="$BIN_DIR/$APP_NAME"
    rm -f "$LAUNCHER"

    # Remove desktop entry
    DESKTOP_FILE="${XDG_DATA_HOME:-$HOME/.local/share}/applications/dockym.desktop"
    rm -f "$DESKTOP_FILE"

    ok "Dockym ha sido desinstalado"
}

# ─── Main ──────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}${CYAN}  ╭──────────────────────────────────╮${NC}"
    echo -e "${BOLD}${CYAN}  │         🐳  Dockym               │${NC}"
    echo -e "${BOLD}${CYAN}  │  Gestor visual de Docker Compose  │${NC}"
    echo -e "${BOLD}${CYAN}  ╰──────────────────────────────────╯${NC}"
    echo ""

    # Handle uninstall
    if [ "${1:-}" = "--uninstall" ] || [ "${1:-}" = "uninstall" ]; then
        uninstall
        exit 0
    fi

    check_python
    check_pkg_managers
    install_deps
    verify_install
    setup_desktop_entry
    print_summary
}

main "$@"
