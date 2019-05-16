# LaTeX summary #

Python scripts which automatically generates a summary of large
latex documents. Parse your document and generates another valid latex
files containing all the sections and items marked as todo in the comments
of the document.

## What it does ##

Turns a latex document:

```latex
\section{Sample section}

%!TODO: Actually put text instead of lorem ipsum.
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

%!SUMMARY: Lorem ipsum dolor sit amet, consectetur adipisicing elit.

\subsection{Sample subsection}

Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

```

Into a summarised LaTeX document:
```latex
\section{Sample section}
    \begin{itemize}[noitemsep]
        \item Actually put text instead of lorem ipsum.
        \item Lorem ipsum dolor sit amet, consectetur adipisicing elit.
    \end{itemize}
\subsection{Sample subsection}
```


## Usage ##

This python scripts parses tex files looking for certain keywords, when these
are matched this lines are captured and added to a summary file. Lines

### In Latex ###
Write your latex document using normal latex sectionning commands 
(non-exhaustive list below). These are all captured and added as is
in the summary file.

 + `\chapter`
 + `\section` (and any number of subsection)
 + etc...

In addition some specially formatted comments will be parsed and itemized
inside the summary document. These comments are:

 + `%!TODO: <your todo note>`
 + `%!SUMMARY: <your summary note>` (with any number of `M`s and `R`s).

For these comments everything after the `:` is captured
until a sentence terminating mark is encountered (`.!?`) or an end of line.


### Building the summary document ###

Call this script using:

	python latex_summary.py your/main/latex_file.tex

This will generate file : `your/main/latex_file_auto_summary.tex`. Which can 
then be built by including it into a document (example below).

### Sample document used generate the summary as a PDF ###

```latex

\documentclass[]{memoir}
\usepackage{enumitem}
\begin{document}

\renewcommand{\contentsname}{Table of Contents}
\tableofcontents*
\addtocontents{toc}{\par\nobreak \mbox{}\hfill{\bf Page}\par\nobreak}


\input{your/main/latex_file_auto_summary}

\end{document}

```

## Limitations ##

 + Parses text one by line: section names must be finished before a line 
 ending is encountered. 


## Sublime Text Integration ##
 
A nicer integration in sublime text can be achieved by adding snippets.
These allow auto completion using less verbose shortcuts. The following two are included:
 
 + Type `%todo` <kbd>TAB</kbd> completes to `%!TODO: `
 + Type `%sum` <kbd>TAB</kbd> completes to `%!SUMMARY: `


#### Snippet to add a todo:

```html
<snippet>
	<content><![CDATA[
%!TODO: ${1:this}.
]]></content>
	<tabTrigger>%todo</tabTrigger>
	<scope>text.tex.latex</scope>
</snippet>
```

#### Snippet to add a summary item:

```html
<snippet>
	<content><![CDATA[
%!SUMMARY: ${1:this}.
]]></content>
		<!-- Optional: Set a tabTrigger to define how to trigger the snippet -->
	<tabTrigger>%sum</tabTrigger>
		<!-- Optional: Set a scope to limit where the snippet will trigger -->
	<scope>text.tex.latex</scope>
</snippet>
```