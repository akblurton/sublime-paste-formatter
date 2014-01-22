
import sublime, sublime_plugin, sys, re, html, subprocess, os, sys


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

HTML_FORMATTER_OPTIONS = [
	"use_strong",
	"use_em",
	"allowed_tags",
	"remove_preceeding_whitespace",
	"remove_linebreak",
	"remove_wrap"
]
HTML_SUPPORTED_OS = ["darwin"]



class PasteFormatted(sublime_plugin.TextCommand):
	def toggle_setting(self, toggle, value): #Toggle a setting in the user's config
		# Ignore invalid settings
		if not toggle in FORMATTER_OPTIONS:
			return

		# Load the current settings object and assign the formatter value
		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		formatter = settings.get("paste_formatter")		
		formatter[toggle] = bool(value)

		# Re-assign the formatter object and save
		settings.set("paste_formatter", formatter)
		sublime.save_settings('PasteFormatter.sublime-settings')

	# Merge settings between user/default settings file and the current project setting
	# optionally filtered by valid
	def merge_settings(self, key, valid = None):
		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		projectSettings = sublime.active_window().active_view().settings()

		# The default/user settings object does not contain this key, return None
		if not settings.has(key):
			return None
		# If the project settings does not contain the given key, return the default/user settings object untouched
		if not projectSettings.has(key):
			return settings.get(key)

		obj = settings.get(key)
		pObj = projectSettings.get(key)

		# Only merge when class types are identical
		if obj.__class__.__name__ != pObj.__class__.__name__:
			return obj

		# Merge lists, with the project having precedence
		if isinstance(obj, list):
			return pObj + obj

		# Merge dictionaries, optionally filtered by valid
		if isinstance(obj, dict):
			for key in obj:
				# Ignore invalid keys
				if isinstance(valid, list) and key not in valid:
					continue
				if key in pObj:
					obj[key] = pObj[key]
			return obj

		# None list/dict items will just return the project setting
		return pObj

	# Retrieve HTML content from the clipboard using external applications
	def html_from_clipboard(self):
		platform = sys.platform
		if platform not in HTML_SUPPORTED_OS: #Only return values for supported operating systems
			return None

		output = ""
		# Mac based clipboard grab
		if platform == "darwin":
			proc = subprocess.Popen([os.path.dirname (__file__) + "/html_clipboard"], stdout=subprocess.PIPE) #Open the html_clipboard obj-c application
			output, err = proc.communicate() # Grab the stdout and assign it to output

		# If no output was retrieved or the application failed, return None
		if not output or proc.returncode is not 0:
			return None

		html_formatter = self.merge_settings("paste_html_formatter")

		# Clean up the HTML
		# output is returned as a byte literal and needs converting to utf-8 for processing
		output = output.decode("utf-8")
		# remove all content before the body tag
		preBody = re.compile(r'^.*<body.*?>', re.I | re.S)
		# remove all content after the body tag
		postBody = re.compile(r'</body.*?>.*$', re.I | re.S)
		# strip all tags that are not allowed
		okayTags = re.compile(r'<(?!/?(strong|b|i|em|sup|sub))[^>]*>', re.I)
		# remove all style tags and their contents
		stripStyle = re.compile (r'<style.*?>[^<]</style>', re.I)
		# remove attributes from tags
		removeAttr = re.compile (r'<([A-Z]+)[^>]*?>', re.I)
		# some applications over complicate html (e.g. <tag>word</tag><tag>word</tag>) this reduces them
		simplify = re.compile (r'</([A-Z]+)>\s*<\1>', re.I)

		# run the regular expressions to clean up output
		output = preBody.sub('', output)
		output = postBody.sub('', output)
		output = stripStyle.sub('', output)
		output = okayTags.sub(r'', output)
		output = removeAttr.sub(r'<\1>', output)
		output = simplify.sub(r'', output)
		output = re.sub(r'^\s+', '', output)
		output = re.sub(r'\s+$', '', output)

		# Sometimes the returned HTML is wrapped to a specific line length, this option removes that by detecting a line break and a single space 
		if html_formatter.get("remove_wrap"):
			output = re.sub(r'\n\r? ', ' ', output)
		return output

	def is_visible(self, **args):
		#Do not display the HTML paste command on unsupported OSes
		if "html" in args and args["html"] is True and sys.platform not in HTML_SUPPORTED_OS: 
			return False

		# Disable toggle commands that represent the current formatter value
		settings = sublime.load_settings('PasteFormatter.sublime-settings')
		formatter = settings.get("paste_formatter")
		if "toggle" in args and "value" in args and args["toggle"] in formatter and formatter[args["toggle"]] is args["value"]:
			return False
		return True		

	#Paste with formatting
	def run(self, edit, **args): 
		# If toggle is provided, change a setting value and exit
		if 'toggle' in args and 'value' in args:
			self.toggle_setting(args['toggle'], args['value'])
			return

		# Run the HTML parser if html:true is given
		htmlParsed = False
		if "html" in args and args ["html"] is True:
			htmlParsed = self.html_from_clipboard()		

		clipboard = sublime.get_clipboard()
		if htmlParsed:
			clipboard = htmlParsed

		# Get formatter settings
		formatter = self.merge_settings("paste_formatter", FORMATTER_OPTIONS)

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
			clipboard = re.sub(r'([^\S\n]){2,}', r' ', clipboard)

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

		if escapeHTML and not htmlParsed: # Escape HTML entities where applicable
			clipboard = html.escape(clipboard, escapeQuotes)

		if autoSup: # Auto-magically superscript ® symbols
			clipboard = re.sub(r"(?<!<(sup|SUP)>) *(®|&reg;)", r"<sup>\2</sup>", clipboard)

		if nltobr: # Convert new lines to br tags
			clipboard = re.sub(r"(\n\r?)", r"<br>\1", clipboard)

		customFormatter = []
		if custom:
			customFormatter = self.merge_settings("paste_formatter_custom")
			if not customFormatter:
				customFormatter = []

		# For each region run any custom formatters and then insert the formatted clipboard contents
		for region in self.view.sel():
			clip = clipboard
			clip = self.execute_custom(clip, customFormatter, min(region.a, region.b), bool(htmlParsed))
			self.view.replace(edit, region, clip)

		# Place the cursor at the end of each paste (rather than having the new content selected)
		regions = []
		for region in self.view.sel():
			region.a = region.b = max(region.a, region.b)
			regions.append(region)

		self.view.sel().clear()
		self.view.sel().add_all(regions)
			

	#Runs custom formatters
	def execute_custom(self, clipboard, formatters, point, isHTML):
		ran = []
		for f in formatters:
			# Each formatter must be a dictionary
			if not isinstance(f, dict):
				continue
			
			# At minimum a find and replace key need to exist in the formatter definition
			if not "find" in f or not "replace" in f:
				continue

			# Ignore any formatters that require a specific paste mode (HTML vs. plain) and do not match the current mode
			if "mode" in f and ((f["mode"] == "html" and not isHTML) or (f["mode"] == "plain" and isHTML)):
				continue

			# Ignore if the given ID has already been run by another formatter
			if "id" in f and "id" in ran:
				continue

			# Ignore formatters that require a specific scope
			if "scope" in f and self.view.score_selector(point, f["scope"]) == 0:
				continue

			# Add the id of this formatter to ran[]
			if "id" in f:
				ran.append(f["id"])

			find = f["find"]
			replace = f["replace"]

			#Get formatter type
			if "type" in f:
				t = f["type"] 
			else:
				t = "text"

			# Text formatters will do a simple string replace
			if t == "text":
				clipboard = clipboard.replace(find, replace)
			# Regex formatters will use the re.sub command
			elif t == "regex":
				clipboard = re.sub(find, replace, clipboard)
			# Eval formatters are more complicated and require returning a lambda function via eval()
			elif t == "eval":
				try:
					print("Pasted formatted: evaluating")
					clipboard = re.sub(find, eval("lambda m: " + replace), clipboard)
				except Exception:
					# Output to the console that a formatter failed to execute
					print("Paste formatted: Eval failed: ", replace)
					# Execute prematurely on a failed formatter
					return clipboard

		return clipboard