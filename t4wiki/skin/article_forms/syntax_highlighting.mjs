import {CodeJar} from 'codejar';
import { Prism } from 'prismjs';

Prism.languages.bibtex = {
	'comment': /%.*/,
	
	/*
	 * section or chapter headlines are highlighted as bold so that
	 * they stand out more
	 */
	'entry-type': {
		pattern: /@[a-z]+/
	},
	
	'citekey': {
		pattern: /(\{)(\w+)/,
		lookbehind: true
	},

	'string': {
		pattern: /".*"/,
		greedy: false
	},
	
	'punctuation': /[[\]{}&]/
};

Prism.languages.wikkly = {
	'comment': {
		pattern: /\/%.*%\//,
		greedy: false
	},
	
	'wikkly-footnote': {
		pattern: /<<footnote.*>>/,
		greedy: false
	},

	'wikkly-italic': {
		pattern: /\/\/[^\/]*\/\//,
		greedy: false
	},

	'wikkly-bold': {
		pattern: /''[^']*''/,
		greedy: false
	},

	'wikkly-heading': {
		pattern: /(^|\n)!+\s*.*/		
	},

	'wikkly-enumeration': {
		pattern: /(^|\n)[#•\*Ⅰ-ↁ]+/
	},
	
	'macro': {
		pattern: /(<<)[a-zA-Z]+\s+/,
		lookbehind: true,
		alias: 'variable'
	},

	'link': {
		pattern: /(\[\[)[^\]]*(?=\]\])/,
		greedy: false,
		lookbehind: true
	},
	
	'punctuation': /[[\]{}&"']|<<|>>/
};


export function init_editor(node) {
	const textarea = node.querySelector("textarea"),
		  viewer = node.querySelector(".source-viewer");

	viewer.textContent = textarea.value;

	let jar = CodeJar(viewer, function(node) {
		Prism.highlightElement(node, false);
	}, { addClosing: false, catchTab: false });

	viewer.jar = jar;
	
	jar.onUpdate(code => {
		textarea.value = viewer.textContent;
	});
}

