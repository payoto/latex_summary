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
 + `%!MULTILINE: <continues the previous note>`
 + `%!MUDDLE: <Creates an item coloured in OliveGreen>`
 + `%!PLAN: <Your planned text/section will appear in blue>`
 + `%!REPEAT: <repeated idea here in DarkOrchid>`

For these comments everything after the `:` is captured
until a sentence terminating mark is encountered (`.!?`) or an end of line.
Any of these comment formats can be altered to go to the end of line, ignoring
sentence terminating punctuation by prepending them with `EOL[ _]*`, valid formats are:

 + `%!EOL TODO...`
 + `%!EOL_TODO...`
 + `%!EOLTODO...`


### Building the summary document ###

Call this script using:

	python latex_summary.py your/main/latex_file.tex

This will generate file : `your/main/latex_file_auto_summary.tex`. Which can 
then be built by including it into a document (example below).

### Sample document used generate the summary as a PDF ###

```latex

\documentclass[]{memoir}
\usepackage{enumitem}
\usepackage[dvipsnames]{xcolor}

\begin{document}

\input{your/main/latex_file_auto_summary}

\end{document}

```

A working example is available in the `test/` folder.

## Limitations and known issues ##

 + Parses text one by line: section names must be finished before a line 
 ending is encountered. 
 + Using package `xcolor` can play up if also using package `tikz` leading to 
 undefined color names when trying to build documents. In that case replace:
 `\usepackage[dvipsnames]{xcolor}` with `\documentclass[usenames,dvipsnames]{beamer}`.


## Sublime Text Integration ##
 
A nicer integration in sublime text can be achieved by adding snippets.
These allow auto completion using less verbose shortcuts. The following six are included:
 
 + Type `%todo` <kbd>TAB</kbd> completes to `%!TODO: `
 + Type `%sum` <kbd>TAB</kbd> completes to `%!SUMMARY: `
 + Type `%mud` <kbd>TAB</kbd> completes to `%!MUDDLE: `
 + Type `%plan` <kbd>TAB</kbd> completes to `%!PLAN: `
 + Type `%mult` <kbd>TAB</kbd> completes to `%!MULT: `
 + Type `%rep` <kbd>TAB</kbd> completes to `%!REPEAT: `


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

#### Snippet to add a other items:

How to make your own snippet for a custom trigger, replace text surrounded by `|`:

```html
<snippet>
	<content><![CDATA[
%!|TYPE OF ITEM|: ${1:this}.
]]></content>
		<!-- Optional: Set a tabTrigger to define how to trigger the snippet -->
	<tabTrigger>|SHORT FORM|</tabTrigger>
		<!-- Optional: Set a scope to limit where the snippet will trigger -->
	<scope>text.tex.latex</scope>
</snippet>
```

### Tips ###

I like to have highlighting of the ToDos, the plans and the muddles in the text. This can
be done with the 
[HighlightWords package](https://packagecontrol.io/packages/HighlightWords).
Settings need to be customised the values to set for good integration are:

```json
{
	"permanent_highlight_keyword_color_mappings": [
		{
			"keyword": "%! *(NI[_ ]*| *)TODO\\h*:[^.!?\n]*[.!?]*(\\n\\h*%!\\h*MULT.*)*",
			"color": "string", "flag": 0
		},
		{
			"keyword": "%! *EOL[_ ]*TODO\\h*:[^\n]*(\\n\\h*%!\\h*MULT.*)*",
			"color": "string", "flag": 0
		},
		{
			"keyword": "%! *(NI[_ ]*| *)(MUDDLE|PLAN)\\h*:[^.!?\n]*[.!?]*(\\n\\h*%!\\h*MULT.*)*",
			"color": "text.tex.latex ", "flag": 0
		},
		{
			"keyword": "%! *EOL[_ ]*(MUDDLE|PLAN)\\h*:[^\n]*(\\n\\h*%!\\h*MULT.*)*",
			"color": "text.tex.latex ", "flag": 0
		},
	],
}
```

These regexp are more restrictive than the python parser's, this is on purpose as 
these are fairly readable when written out.

Eplanation:
 
 + `%!(NI[_ ]*|EOL[_ ]*| *)` capture the `%!` directive with any of the NI or EOL modifiers.
 + `(TODO|PLAN|MUDDLE)` capture the type of directive.
 + `\\h*:` Capture any whitespaces and trailing colon (colon is required).
 + `[^.!?\n]*[.!?]*` Capture until the end of the sentence.
 + `(\\n\\h*%!\\h*MULT.*)*` Capture any following line with the multiline directive.

### Version ###

1.0.0