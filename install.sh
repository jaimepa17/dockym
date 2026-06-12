#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────
#  Dockym — Installer
#  https://github.com/jaimepa17/dockym
#
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/jaimepa17/dockym/main/install.sh | bash
#    curl -fsSL https://raw.githubusercontent.com/jaimepa17/dockym/main/install.sh | bash -s -- --binary
#    curl -fsSL https://raw.githubusercontent.com/jaimepa17/dockym/main/install.sh | bash -s -- --uninstall
#    curl -fsSL https://raw.githubusercontent.com/jaimepa17/dockym/main/install.sh | bash -s -- --pip
#    curl -fsSL https://raw.githubusercontent.com/jaimepa17/dockym/main/install.sh | bash -s -- --uv
#
#  Flags:
#    --binary     Force download pre-built binary from latest GitHub Release
#    --pip        Force install via pip (from PyPI or GitHub)
#    --uv         Force install via uv tool install
#    --version    Install a specific version (e.g. --version 0.1.0)
#    --uninstall  Remove Dockym
# ──────────────────────────────────────────────────────

REPO="jaimepa17/dockym"
APP_NAME="dockym"
INSTALL_DIR="${DOCKYM_DIR:-$HOME/.local/share/dockym}"
BIN_DIR="${DOCKYM_BIN_DIR:-$HOME/.local/bin}"

# ─── Colores ────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Helpers ────────────────────────────────────────
info()    { echo -e "${BLUE}::${NC} $1"; }
ok()      { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; }
header()  { echo -e "\n${BOLD}── $1 ──${NC}\n"; }
die()     { error "$1"; exit 1; }

ensure_dirs() {
    mkdir -p "$INSTALL_DIR" "$BIN_DIR"
}

# ─── Platform detection ─────────────────────────────
detect_platform() {
    local arch
    arch=$(uname -m)
    case "$(uname -s)" in
        Linux)
            if [ "$arch" = "x86_64" ]; then
                echo "linux-x86_64"
            else
                echo "linux-$arch"
            fi
            ;;
        Darwin)
            if [ "$arch" = "arm64" ]; then
                echo "macos-arm64"
            else
                echo "macos-x86_64"
            fi
            ;;
        *)
            die "Sistema operativo no soportado: $(uname -s)"
            ;;
    esac
}

# ─── Check commands availability ────────────────────
require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        die "Se requiere '$1' pero no está instalado."
    fi
}

# ─── Binary install (from GitHub Release) ──────────
install_binary() {
    header "Descargando binario pre-compilado"
    ensure_dirs

    local platform version ext url archive extract_dir
    platform=$(detect_platform)
    version="${INPUT_VERSION:-latest}"

    require_cmd curl

    if [ "$version" = "latest" ]; then
        info "Obteniendo última versión..."
        version=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
            | grep '"tag_name":' \
            | sed -E 's/.*"v([^"]+)".*/\1/')
        if [ -z "$version" ]; then
            warn "No se pudo determinar la última versión. ¿Hay algún release publicado?"
            warn "Usando la versión desde código fuente como fallback..."
            return 1
        fi
        ok "Última versión: v$version"
    fi

    # Map platform to artifact file
    case "$platform" in
        linux-x86_64) artifact="dockym-linux-x86_64.tar.gz" ;;
        macos-arm64)  artifact="dockym-macos-arm64.zip" ;;
        macos-x86_64) artifact="dockym-macos-x86_64.zip" ;;
        *)            die "No hay binario pre-compilado para $platform" ;;
    esac

    url="https://github.com/$REPO/releases/download/v$version/$artifact"
    info "Descargando: $url"

    archive="$INSTALL_DIR/$artifact"
    curl -fsSL "$url" -o "$archive" || {
        warn "No se pudo descargar el binario para v$version ($platform)."
        warn "Probando instalación desde código fuente..."
        return 1
    }

    ok "Descargado ($(du -h "$archive" | cut -f1))"

    case "$artifact" in
        *.tar.gz)
            tar xzf "$archive" -C "$INSTALL_DIR"
            extract_dir=$(tar tzf "$archive" | head -1 | cut -d/ -f1)
            ;;
        *.zip)
            require_cmd unzip
            unzip -qo "$archive" -d "$INSTALL_DIR"
            # Buscar el .app o ejecutable
            extract_dir=$(unzip -l "$archive" 2>/dev/null | head -4 | tail -1 | awk '{print $NF}' | cut -d/ -f1)
            ;;
    esac

    # Create launcher symlink
    if [ -d "$INSTALL_DIR/$extract_dir/$APP_NAME.app" ]; then
        # macOS .app bundle
        ln -sf "$INSTALL_DIR/$extract_dir/$APP_NAME.app" "$INSTALL_DIR/$APP_NAME.app"
        # Create a CLI launcher that opens the app
        cat > "$BIN_DIR/$APP_NAME" << LAUNCHER_EOF
#!/usr/bin/env bash
open "$INSTALL_DIR/$APP_NAME.app"
LAUNCHER_EOF
        chmod +x "$BIN_DIR/$APP_NAME"
        ok "macOS .app bundle instalado en $INSTALL_DIR/$APP_NAME.app"
    elif [ -f "$INSTALL_DIR/$extract_dir/$APP_NAME" ]; then
        # Linux executable
        ln -sf "$INSTALL_DIR/$extract_dir/$APP_NAME" "$BIN_DIR/$APP_NAME"
        chmod +x "$BIN_DIR/$APP_NAME"
    fi

    rm -f "$archive"
    return 0
}

# ─── Python version check ──────────────────────────
check_python() {
    header "Verificando Python"

    PYTHON=""
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    done

    if [ -z "$PYTHON" ]; then
        error "Python no está instalado."
        echo "  Instálalo desde: https://www.python.org/downloads/"
        echo "  O con tu gestor de paquetes:"
        echo "    Arch Linux:       sudo pacman -S python python-pip"
        echo "    Debian/Ubuntu:    sudo apt install python3 python3-pip python3-venv"
        echo "    Fedora:           sudo dnf install python3 python3-pip"
        echo "    macOS (Homebrew): brew install python@3.11"
        die "Python ≥ 3.11 es requerido"
    fi

    version=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
    major=${version%.*}
    minor=${version#*.}

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
        die "Se requiere Python ≥ 3.11 (tienes: $($PYTHON --version 2>&1))"
    fi

    ok "Python $($PYTHON --version 2>&1)"
}

# ─── Install via uv ────────────────────────────────
install_uv() {
    header "Instalando con uv"

    ensure_dirs
    require_cmd uv

    info "Ejecutando: uv tool install dockym..."
    if uv tool install --reinstall "git+https://github.com/$REPO.git" 2>&1 | sed 's/^/  /'; then
        ok "Instalado con uv correctamente"
        return 0
    fi

    warn "Falló la instalación con uv"
    return 1
}

# ─── Install via pip ───────────────────────────────
install_pip() {
    header "Instalando con pip"

    ensure_dirs

    require_cmd "$PYTHON"

    # Try from PyPI first, fallback to GitHub
    local source="dockym"
    info "Probando instalación desde PyPI..."
    if $PYTHON -m pip install --quiet --upgrade "$source" 2>/dev/null; then
        ok "Instalado desde PyPI"
    else
        info "Instalando directamente desde GitHub..."
        source="git+https://github.com/$REPO.git"
        $PYTHON -m pip install --quiet --upgrade "$source" 2>&1 | sed 's/^/  /' || {
            # Last resort: create venv
            warn "Instalación global falló. Probando con entorno virtual..."
            local venv_dir="$INSTALL_DIR/venv"
            $PYTHON -m venv "$venv_dir"
            "$venv_dir/bin/pip" install --quiet --upgrade "git+https://github.com/$REPO.git"
            cat > "$BIN_DIR/$APP_NAME" << LAUNCHER_EOF
#!/usr/bin/env bash
exec "$venv_dir/bin/$APP_NAME" "\$@"
LAUNCHER_EOF
            chmod +x "$BIN_DIR/$APP_NAME"
        }
    fi

    ok "Instalado con pip correctamente"
}

# ─── Verify installation ──────────────────────────
verify_install() {
    header "Verificando instalación"

    if command -v "$APP_NAME" &>/dev/null; then
        ok "✅ $APP_NAME está disponible en el PATH"
        echo ""
        echo -e "  ${BOLD}Ejecuta:${NC}  ${CYAN}$APP_NAME${NC}"
    elif [ -x "$BIN_DIR/$APP_NAME" ]; then
        warn "⚠️  $APP_NAME está en $BIN_DIR pero no está en el PATH"
        echo ""
        echo -e "  Para usarlo, agrega a tu ${BOLD}~/.bashrc${NC} o ${BOLD}~/.zshrc${NC}:"
        echo -e "  ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
        echo ""
        echo -e "  Después: ${CYAN}source ~/.bashrc && $APP_NAME${NC}"
    elif [ -d "$INSTALL_DIR/$APP_NAME.app" ]; then
        ok "✅ $APP_NAME.app instalado en $INSTALL_DIR"
        echo ""
        echo -e "  Ejecuta: ${CYAN}open $INSTALL_DIR/$APP_NAME.app${NC}"
    else
        warn "No se pudo verificar la instalación automáticamente."
        echo "  Busca el ejecutable en: $INSTALL_DIR/"
        echo "  O ejecuta: $PYTHON -m dockym"
    fi
}

# ─── Desktop entry (Linux) ─────────────────────────
setup_desktop_entry() {
    [ "$(uname)" != "Linux" ] && return

    header "Acceso directo (Linux)"

    local app_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    local desktop_file="$app_dir/dockym.desktop"
    local exec_path

    exec_path=$(command -v "$APP_NAME" 2>/dev/null || echo "$BIN_DIR/$APP_NAME")

    mkdir -p "$app_dir"

    cat > "$desktop_file" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Name=Dockym
Comment=Gestor visual de servicios Docker Compose
Exec=$exec_path
Icon=dockym
Terminal=false
Type=Application
Categories=Development;System;Utility;
Keywords=docker;compose;containers;devops;
StartupWMClass=dockym
DESKTOP_EOF

    # Generate a simple PNG icon (48x48, solid color with letter D)
    if command -v "$PYTHON" &>/dev/null; then
        local icon_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/48x48/apps"
        mkdir -p "$icon_dir"
        "$PYTHON" -c "
import struct, zlib

def create_png(width, height, color, filepath):
    def chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    header = b'\\x89PNG\\r\\n\\x1a\\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    raw = b''
    for y in range(height):
        raw += b'\\x00'
        for x in range(width):
            raw += bytes(color)
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    with open(filepath, 'wb') as f:
        f.write(header + ihdr + idat + iend)

icon_path = '$icon_dir/dockym.png'
if not __import__('os').path.exists(icon_path):
    create_png(48, 48, (38, 132, 255), icon_path)
    print(f'  Icono creado: {icon_path}')
" 2>/dev/null || true
    fi

    ok "Entrada de escritorio creada: $desktop_file"
}

# ─── Summary ────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${GREEN}┌────────────────────────────────────────────┐${NC}"
    echo -e "${GREEN}│${NC}  ✅  Dockym se instaló correctamente       ${GREEN}│${NC}"
    echo -e "${GREEN}└────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "  ${BOLD}Ejecutar:${NC}  ${CYAN}$APP_NAME${NC}"
    echo ""
    echo -e "  📖  Documentación: https://github.com/$REPO"
    echo -e "  🐛  Reportar bugs: https://github.com/$REPO/issues"
    echo ""
}

# ─── Uninstall ──────────────────────────────────────
uninstall() {
    header "Desinstalando Dockym"

    # Remove uv tool
    if command -v uv &>/dev/null; then
        uv tool uninstall dockym 2>/dev/null || true
    fi

    # Remove install dir
    rm -rf "$INSTALL_DIR"

    # Remove launcher
    rm -f "$BIN_DIR/$APP_NAME"

    # Remove desktop entry
    rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/dockym.desktop"

    # Remove icon
    rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/48x48/apps/dockym.png"

    ok "Dockym ha sido desinstalado completamente"
}

# ─── Flags ─────────────────────────────────────────
FORCE_BINARY=false
FORCE_UV=false
FORCE_PIP=false
INPUT_VERSION=""

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --binary)    FORCE_BINARY=true ;;
            --uv)        FORCE_UV=true ;;
            --pip)       FORCE_PIP=true ;;
            --version)   shift; INPUT_VERSION="$1" ;;
            --uninstall) uninstall; exit 0 ;;
            uninstall)   uninstall; exit 0 ;;
            -h|--help)
                echo "Uso: curl -fsSL ... | bash -s -- [flags]"
                echo ""
                echo "Flags:"
                echo "  --binary      Descargar binario pre-compilado (GitHub Release)"
                echo "  --uv          Instalar con uv tool install"
                echo "  --pip         Instalar con pip"
                echo "  --version X   Especificar versión (ej: 0.1.0)"
                echo "  --uninstall   Desinstalar Dockym"
                exit 0
                ;;
            *) warn "Flag desconocido: $1. Continuando..." ;;
        esac
        shift
    done
}

# ─── Main ───────────────────────────────────────────
main() {
    parse_args "$@"

    echo ""
    echo -e "${BOLD}${CYAN}  ╭──────────────────────────────────╮${NC}"
    echo -e "${BOLD}${CYAN}  │         🐳  Dockym               │${NC}"
    echo -e "${BOLD}${CYAN}  │  Gestor visual de Docker Compose  │${NC}"
    echo -e "${BOLD}${CYAN}  ╰──────────────────────────────────╯${NC}"
    echo ""

    # ── Binary mode (fast path) ──────────────
    if [ "$FORCE_BINARY" = true ]; then
        install_binary && { verify_install; setup_desktop_entry; print_summary; exit 0; }
        die "Falló la descarga del binario. Usa --uv o --pip como alternativa."
    fi

    # ── Single method requested ──────────────
    if [ "$FORCE_UV" = true ]; then
        check_python
        install_uv || die "Falló la instalación con uv"
        verify_install
        setup_desktop_entry
        print_summary
        exit 0
    fi

    if [ "$FORCE_PIP" = true ]; then
        check_python
        install_pip
        verify_install
        setup_desktop_entry
        print_summary
        exit 0
    fi

    # ── Auto mode: binary → uv → pip ─────────
    # First try: pre-built binary (fastest)
    if install_binary; then
        verify_install
        setup_desktop_entry
        print_summary
        exit 0
    fi

    # Second try: uv
    check_python
    if command -v uv &>/dev/null; then
        if install_uv; then
            verify_install
            setup_desktop_entry
            print_summary
            exit 0
        fi
    fi

    # Third try: pip
    install_pip
    verify_install
    setup_desktop_entry
    print_summary
}

main "$@"
