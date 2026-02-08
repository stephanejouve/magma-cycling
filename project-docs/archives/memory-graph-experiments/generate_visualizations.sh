#!/bin/bash
# Generate PDF visualizations once Graphviz is installed

echo "Checking Graphviz installation..."
if ! command -v dot &> /dev/null; then
    echo "❌ Graphviz not found. Admin needs to install it first:"
    echo "   sudo chown -R stephanejouve /usr/local/Cellar /usr/local/bin"
    echo "   brew install graphviz"
    exit 1
fi

echo "✅ Graphviz found at: $(which dot)"
echo ""

echo "Generating PDF visualizations..."
cd "$(dirname "$0")"

# Generate from simple examples
for gv_file in example*.gv; do
    if [ -f "$gv_file" ]; then
        pdf_file="${gv_file%.gv}.pdf"
        echo "  📄 $gv_file -> $pdf_file"
        dot -Tpdf "$gv_file" -o "$pdf_file"
    fi
done

# Generate from planning examples
for gv_file in memory_graph*.gv; do
    if [ -f "$gv_file" ]; then
        pdf_file="${gv_file%.gv}.pdf"
        echo "  📄 $gv_file -> $pdf_file"
        dot -Tpdf "$gv_file" -o "$pdf_file"
    fi
done

echo ""
echo "✅ All visualizations generated!"
echo "   Open them with: open *.pdf"
