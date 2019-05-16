# LaTeX summary #

Python scripts which automatically generates a summary of large
latex documents. Parse your document and generates another valid latex
files containing all the sections and items marked as todo in the comments
of the document.

# Usage #
### In Latex ###
Write your latex document using normal latex sectionning commands 
(non-exhaustive list):

 + `\chapter`
 + `\section` (and any number of subsection)
 + etc...

In addition some specially formatted comments will be parsed and itemized
inside the summary document the commands are:

 + `%!TODO: <your todo note>`
 + `%!SUMMARY: <your summary note>` (with any number of `M`s and `R`s).

### Building the summary document ###

Call this script using:

	python latex_summary.py your/main/latex_file.tex

This will generate file : `your/main/latex_file_auto_summary.tex`. Which can 
then be built by including it into a document (example below).

### Sample document used generate the summary as a PDF ###

```latex

\documentclass[]{memoir}

\begin{document}

\renewcommand{\contentsname}{Table of Contents}
\tableofcontents*
\addtocontents{toc}{\par\nobreak \mbox{}\hfill{\bf Page}\par\nobreak}


\input{your/main/latex_file_auto_summary}

\end{document}

```