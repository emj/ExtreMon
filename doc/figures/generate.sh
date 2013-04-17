#!/bin/bash
#---------------------------------------------------------------------------------------------
# generate cropped eps from LaTex documents

rm *.{aux,dvi,log,pdf,ps,xdv}

for sourcefile in *.tex; do
	sourcename=`echo $sourcefile | cut -d '.' -f 1`
	if [ ! -f "${sourcename}.eps" -o "${sourcename}.tex" -nt "${sourcename}.eps" ]; then
		echo "Generating ${sourcename}"
		latex ${sourcename}.tex
		dvips ${sourcename}.dvi
		ps2pdf -dAutoRotatePages=/None ${sourcename}.ps

		echo "Generating ${sourcename}"
		latex ${sourcename}.tex
		dvips ${sourcename}.dvi
		ps2pdf -dAutoRotatePages=/None ${sourcename}.ps

		# from pdf2eps by Herbert Voss - see http://tug.org/PSTricks/pdf/pdf2eps
		pdfcrop ${sourcename}.pdf
		pdftops -f 1 -l 1 -eps "${sourcename}-crop.pdf"
		rm  "${sourcename}-crop.pdf"
		mv  "${sourcename}-crop.eps" ${sourcename}.eps
	else
		echo "${sourcename} is up-to-date"
	fi
done
