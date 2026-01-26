CURRENT_DIR="$(pwd)"

mkdir "$CURRENT_DIR/source"
mkdir "$CURRENT_DIR/source/usr" 
mkdir "$CURRENT_DIR/source/usr/share"
mkdir "$CURRENT_DIR/source/usr/share/icons"
mkdir "$CURRENT_DIR/output"
cp -r DEBIAN "$CURRENT_DIR/source/"
bash install.sh -d "$CURRENT_DIR/source/usr/share/icons"

dpkg-deb --build --root-owner-group "$CURRENT_DIR/source" "$CURRENT_DIR/output/vasak-icon-theme_0.5.3_all.deb"  