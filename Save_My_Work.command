cd "$(dirname "$0")"

git add .

git commit -m "Add new products"

git push

echo ""
echo "All done. You can close this window."
read -n 1
