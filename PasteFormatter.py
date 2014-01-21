import sublime, sublime_plugin, sys, re, html

FORMATTER_OPTIONS = [
	"trim",
	"photoshop",
	"clean_whitespace",
	"clean_linebreaks",
	"clean_brackets",
	"remove_bullets",
	"escape_html",
	"escape_quotes",
	"registered_tm",
	"nltobr",
	"allow_custom",
	"clean_punctuation"
]

FORMATTER_TOGGLE_STATEMENTS = {
	"trim" : "whitespace trimming",
	"photoshop" : "photoshop linebreaks",
	"clean_whitespace" : "whitespace cleanup",
	"clean_linebreaks" : "linebreak cleanup",
	"clean_brackets" : "bracket cleanup",
	"clean_punctuation" : "punctuation cleanup",
	"remove_bullets" : "bullet point removal",
	"escape_html" : "html escaping",
	"escape_quotes" : "quote escaping",
	"registered_tm" : "® superscripting",
	"nltobr" : "newline to br tags",
	"allow_custom" : "custom formatting"
}



class PasteFormatted(sublime_plugin.TextCommand):
	editing = ""

	def adjust_setting(self, index):
		if index is -1 or self.editing is "":
			self.editing = ""
			return

		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		formatter = settings.get("paste_formatter")
		
		formatter[self.editing] = index is 0
		settings.set("paste_formatter", formatter)
		sublime.save_settings('PasteFormatter.sublime-settings')

		self.editing = ""


	def toggle_setting(self, toggle): #Toggle a setting in the user's config
		# Ignore invalid settings
		if not toggle in FORMATTER_OPTIONS:
			return

		self.editing = toggle
		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		formatter = settings.get("paste_formatter")
		startIndex = 1
		if formatter.get(toggle) is False:
			startIndex = 0

		options = ["Turn " + FORMATTER_TOGGLE_STATEMENTS[toggle] + " on", "Turn " + FORMATTER_TOGGLE_STATEMENTS[toggle] +  " off"]
		if startIndex == 1:
			options[0] += " (current)"
		else:
			options[1] += " (current)"
		sublime.active_window().show_quick_panel(options, self.adjust_setting, 0, startIndex)

	def run(self, edit, **args): #Paste with formatting
		if 'toggle' in args:
			self.toggle_setting(args['toggle'])
			return

		clipboard = sublime.get_clipboard()

		# Get settings file
		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		projectSettings = sublime.active_window().active_view().settings()
		formatter = settings.get("paste_formatter")

		# merge project settings
		if projectSettings.has("paste_formatter"):
			projectFormatter = projectSettings.get("paste_formatter")
			for opt in FORMATTER_OPTIONS:
				if(opt in projectFormatter):
					formatter[opt] = projectFormatter[opt]


		# Flags for formatting-
		trim = formatter.get("trim")
		photoshopLinebreaks = formatter.get("photoshop")
		cleanWhitespace = formatter.get("clean_whitespace")
		cleanLinebreaks = formatter.get("clean_linebreaks")
		cleanBrackets = formatter.get("clean_brackets")
		cleanPunctuation = formatter.get("clean_punctuation")
		removeBullets = formatter.get("remove_bullets")
		escapeHTML = formatter.get("escape_html")
		escapeQuotes = formatter.get("escape_quotes")
		autoSup = formatter.get("registered_tm")
		nltobr = formatter.get("nltobr")
		custom = formatter.get("allow_custom")

		if photoshopLinebreaks: # Clean up line breaks copied from photoshop/illustrator
			clipboard = clipboard.replace('', '\n')
		
		if trim: # Remove preceeding and trailing whitespace
			clipboard = re.sub(r'^\s*(.*?)\s*$', r'\1', clipboard)

		if cleanWhitespace: # Condense multiple spaces/tabs into one single space
			clipboard = re.sub(r'([ \t]){2,}', r' ', clipboard)

		if cleanLinebreaks: # Condense multiple linebreaks into one
			clipboard = re.sub(r'[\n\r]{2,}', '\n', clipboard)

		if cleanBrackets:
			clipboard = re.sub(r'([^ \]()\[{}])([\[({])', r'\1 \2', clipboard) # Add spaces before brackets
			clipboard = re.sub(r'([\[({])\s+', r'\1', clipboard) # Remove spaces at start of bracket
			clipboard = re.sub(r'\s+([\])}])\s*', r'\1', clipboard) # Remove spaces before the end of a bracket
			# \p{L}\p{M}* represents a single Unicode letter character
			clipboard = re.sub(r'([\])}])(\p{L}\p{M}*|[\w-])', r'\1 \2', clipboard) # Add a space before a word character and a closing bracket

		if cleanPunctuation:
			clipboard = re.sub(r'\s*([!?/;:\.,])', r'\1', clipboard) #Remove spaces before punctuation
			clipboard = re.sub(r'(?<![0-9])([!?/;:\.,])([^!?/;:\.,])', r'\1 \2', clipboard) #Add spaces after punctuation
			clipboard = re.sub(r'(?=<[0-9])([!?/;:\.,])([^!?/;:\.,0-9])', r'\1 \2', clipboard) #Different rules for numbers
			clipboard = re.sub(r'([¿¡]) +', r'\1', clipboard); #Clean spaces on spanish punctuation


		if removeBullets: # Remove preceeding bullets sometimes created by Word/Excel
			clipboard = re.sub(r'•\s*', '', clipboard)

		if escapeHTML: # Escape HTML entities where applicable
			clipboard = html.escape(clipboard, escapeQuotes)

		if autoSup: # Auto-magically superscript ® symbols
			clipboard = re.sub(r"(®|&reg;)", r"<sup>\1</sup>", clipboard)

		if nltobr: # Convert new lines to br tags
			clipboard = re.sub(r"(\n\r?)", r"<br>\1", clipboard)

		customFormatter = []
		if custom:
			customFormatter = settings.get("paste_formatter_custom")
			if not isinstance(customFormatter, list):
				customFormatter = []

			project = projectSettings.get("paste_formatter_custom")
			if isinstance(project, list):
				customFormatter = customFormatter + project

		for region in self.view.sel():
			clip = clipboard
			clip = self.execute_custom(clip, customFormatter, min(region.a, region.b))
			self.view.replace(edit, region, clip)

	def execute_custom(self, clipboard, formatters, point): #Runs custom formatters
		ran = []

		for f in formatters:
			if not isinstance(f, dict):
				continue
			
			if not "find" in f or not "replace" in f:
				continue

			if "id" in f and "id" in ran:
				continue

			if "scope" in f and self.view.score_selector(point, f["scope"]) == 0:
				continue

			if "id" in f:
				ran.append(f["id"])

			find = f["find"]
			replace = f["replace"]

			if "type" in f:
				t = f["type"] #Get formatter type
			else:
				t = "text"

			if t == "text":
				clipboard = clipboard.replace(find, replace)
			elif t == "regex":
				clipboard = re.sub(find, replace, clipboard)
			elif t == "eval":
				try:
					print("Pasted formatted: evaluating")
					clipboard = re.sub(find, eval("lambda m: " + replace), clipboard)
				except Exception:
					print("Paste formatted: Eval failed")
					return clipboard

		return clipboard
