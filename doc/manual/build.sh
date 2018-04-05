#!/bin/bash

if [ $GEM_SET_DEBUG ]; then
    set -x
fi
set -e

function check_errors {
    if cat $1 | grep -qi error; then
        echo "Error detected: failing the build."
        exit 1
    fi
}

# Make current path an absolute path
CURPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERSION="$(cat $CURPATH/../../openquake/baselib/__init__.py | sed -n "s/^__version__[  ]*=[    ]*['\"]\([^'\"]\+\)['\"].*/\1/gp")"
cd $CURPATH

# Generate the cover
sed -i "s/Version X\.Y\.Z/Version $VERSION/" figures/oq_manual_cover.svg
inkscape -A figures/oq_manual_cover.pdf figures/oq_manual_cover.svg

# Update metadata (version, dates...)
sed -i "s/#PUBYEAR#/$(date +%Y)/g; s/#PUBMONTH#/$(date +%B)/g" oq-manual.tex
sed -i "s/version X\.Y\.Z/version $VERSION/; s/ENGINE\.X\.Y\.Z/ENGINE\.$VERSION/" oq-manual.tex

# First batched runs
(pdflatex -shell-escape -interaction=nonstopmode oq-manual.tex
bibtex oq-manual
pdflatex -shell-escape -interaction=nonstopmode oq-manual.tex
makeindex oq-manual.idx
makeglossaries oq-manual
pdflatex -shell-escape -interaction=nonstopmode oq-manual.tex
makeglossaries oq-manual) | tee output.log | egrep -i "error|missing"
# Check for errors
check_errors output.log

# Final run and check for errors
echo -e "\n\n=== FINAL RUN ===\n\n"
pdflatex -shell-escape -interaction=nonstopmode oq-manual.tex | tee -a output.log | grep -iE "error|missing"
# Check for errors
check_errors output.log

# Check if a pdf has been generated and compress it if requested (keeping metadata)
if [ -f oq-manual.pdf ]; then
    ./clean.sh || true
    if [ "$1" == "--compress" ]; then
        pdfinfo "oq-manual.pdf" | sed -e 's/^ *//;s/ *$//;s/ \{1,\}/ /g' -e 's/^/  \//' -e '/CreationDate/,$d' -e 's/$/)/' -e 's/: / (/' > .pdfmarks
        sed -i '1s/^ /[/' .pdfmarks
        sed -i '/:)$/d' .pdfmarks
        echo "  /DOCINFO pdfmark" >> .pdfmarks
        gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/printer -dNOPAUSE -dQUIET -dBATCH -sOutputFile=compressed-oq-manual.pdf oq-manual.pdf .pdfmarks
        mv -f compressed-oq-manual.pdf oq-manual.pdf
    fi
else
    exit 1
fi
