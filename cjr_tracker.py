"""
cjr_tracker.py

A Python script for tracking r/CriminalJusticeReform posts.

To Do:
password persistence.
fix list_sub long usernames.
open reddit submissions
reload reddit data
persistent data lists

Constants:
ACCESS_KWARGS: The standard access credentials. (dict of str: str)
DATA_START: The date that data collection started. (datetime.datetime)

Classes:
Post: A post on r/CriminalJusticeReform. (object)
Tracker: An interface for tracking r/CriminalJusticeReform. (cmdr.Cmdr)

Functions:
check_cjr: Check for new posts in r/CriminalJusticeReform. (list of Submission)
levenshtein: Determine the Levenshtein distance between two strings. (int)
load_keywords: Load the key words for subreddit scanning. (set of str)
load_local: Load the local data. (dict)
load_reddit: Open a line into Reddit. (praw.Reddit)
"""

import datetime as dt
import praw
import re
from urllib.parse import urlparse
import webbrowser

import cmdr

__author__ = 'Craig "Ichabod" O\'Brien'

__version__ = 'v1.2.2'

ACCESS_KWARGS = {'client_id': 'jy2JWMnhs2ZrSA', 'client_secret': 'LsnszIp9j_vVl9cvPDbEPemdyCg',
	'user_agent': f'windows:cjr_tracker:{__version__} (by u/ichabod801)'}

DATA_START = dt.datetime(2020, 4, 1)

class Post(object):
	"""
	A post on r/CriminalJusticeReform. (object)

	Class Attributes:
	all_tags: All of the tags used in various posts. (set of str)
	num_posts: The number of post objects created. (int)

	Attributes:
	comments: The number of comments the post received. (int)
	date: The dat the post was submitted. (dt.datetime)
	notes: Any moderator notes made on the post. (str)
	per_up: The percentage upvoted for the post. (float)
	post_id: The local post identifier. (int)
	poster: The name of the Redditor who made the post. (str)
	reddit_id: The Reddit post identifier. (str)
	score: The Reddit score for the post. (int)
	source: The website linked to. (str)
	submission: The submission object for the post. (None or praw.Submission)
	tags: The tags for the post. (str)
	title: The title of the post. (str)

	Methods:
	_from_line: Intialize a post from local data. (None)
	_from_submission: Initialize a post from Reddit data. (None)
	add_note: Add a note to the post. (None)
	add_tag: Add a tag to the post. (bool)
	data_line: Tab delimited text representation. (str)
	details: A detailed text representation. (str)
	suggest_tags: Find possible matches to a potential tag. (list of str)
	tag_lines: Tab delimited text representation of the post's tags. (str)
	update: Update a Post based on a Submission. (None)

	Overridden Methods:
	__init__
	"""

	num_posts = 0
	all_tags = set()

	def __init__(self, data):
		"""
		Intialize a post from local data. (None)

		Parameters:
		data: Data from a local data set or from Reddit. (str or Submission)
		"""
		if isinstance(data, str):
			self._from_line(data)
		else:
			self._from_submission(data)

	def __repr__(self):
		"""
		Debugging text represenation. (str)
		"""
		return '<Post {} by {}, {:%m/%d/%y}>'.format(self.reddit_id, self.poster, self.date)

	def __str__(self):
		"""
		Human readable text representation. (str)
		"""
		text = '{}  {:<16}  {:<8}  {:<36}  {:>4}'
		date_text = self.date.strftime('%m/%d/%y')
		return text.format(self.reddit_id, self.poster[:16], date_text, self.title[:36], self.score)

	def _from_line(self, line):
		"""
		Intialize a post from local data. (None)

		Parameters:
		line: A line in the local data set.
		"""
		fields = line.split('\t')
		self.post_id = int(fields[0])
		Post.num_posts += 1
		self.reddit_id = fields[1]
		self.date = dt.datetime.strptime(fields[2], '%m/%d/%Y')
		self.source = fields[3]
		self.poster = fields[4]
		self.title = fields[5]
		self.score = int(fields[6]) if fields[6] else 0
		self.per_up = float(fields[7]) if fields[7] else 0.0
		self.comments = int(fields[8]) if fields[8] else 0
		self.notes = fields[9].strip()
		self.tags = []
		self.submission = None

	def _from_submission(self, data):
		"""
		Initialize a post from Reddit data. (None)

		Parameters:
		data: A Reddit submission object. (praw.Submission)
		"""
		Post.num_posts += 1
		self.post_id = Post.num_posts
		self.reddit_id = data.id
		self.date = dt.datetime.fromtimestamp(data.created_utc)
		self.source = urlparse(data.url).netloc
		self.poster = str(data.author)
		self.title = data.title
		self.score = data.score
		self.per_up = data.upvote_ratio
		self.comments = len(data.comments)
		self.notes = ''
		self.tags = []
		self.submission = data

	def add_note(self, note):
		"""
		Add a note to the post. (None)

		Parameters:
		Note: The note to add to the post. (str)
		"""
		if self.notes:
			self.notes = f'{self.notes} | {note}'
		else:
			self.notes = note

	def add_tag(self, tag, force = False):
		"""
		Add a tag to the post. (bool)

		The return value is a flag indicating that the tag was successfully added.
		Tags are not added if they have not been seen before, unless the force
		parameter is True.

		Parameters:
		tag: The tag to add. (str)
		force: A flag for forcing the addition of the tag. (bool)
		"""
		if tag in Post.all_tags:
			self.tags.append(tag)
		elif force:
			self.tags.append(tag)
			Post.all_tags.add(tag)
		else:
			return False
		return True

	def data_line(self):
		"""Tab delimited text representation. (str)"""
		data = [str(self.post_id), self.reddit_id, f'{self.date:%m/%d/%Y}', self.source, self.poster]
		data.extend([self.title, str(self.score), str(self.per_up), str(self.comments), self.notes])
		return '\t'.join(data) + '\n'

	def details(self):
		"""A detailed text representation. (str)"""
		lines = ['Post {} by {} on {:%m/%d/%y} from {}:']
		lines[0] = lines[0].format(self.reddit_id, self.poster, self.date, self.source)
		lines.append('	{}'.format(self.title[:70]))
		lines.append('	Score: {}, %Upvoted: {:.2%}, Comments: {}')
		lines[-1] = lines[-1].format(self.score, self.per_up, self.comments)
		if self.notes:
			lines.append('	Notes: {}'.format(self.notes))
		if self.tags:
			lines.append('	Tags: {}'.format(', '.join(self.tags)))
		return '\n'.join(lines)

	def suggest_tags(self, tag, n = 5):
		"""
		Find possible matches to a potential tag from the existing tags. (list of str)

		Parameters:
		tag: The potential tag to find matches for. (str)
		n: How many tags to suggest. (int)
		"""
		distances = [(levenshtein(tag, existing), existing) for existing in Post.all_tags]
		distances.sort()
		return [tag for distance, tag in distances[:n]]

	def tag_lines(self):
		"""Tab delimited text representation of the post's tags. (str)"""
		if self.tags:
			return ''.join([f'{self.post_id}\t{tag}\n' for tag in self.tags])
		else:
			return ''

	def update(self, submission):
		"""
		Update a Post based on a Submission. (None)

		Parameters:
		submission: The Reddit data to update with. (praw.Submission)
		"""
		base = (self.score, self.per_up, self.comments)
		self.score = submission.score
		self.per_up = submission.upvote_ratio
		self.comments = len(submission.comments)
		self.submission = submission
		return base != (self.score, self.per_up, self.comments)

class Tracker(cmdr.Cmdr):
	"""
	An interface for tracking r/CriminalJusticeReform. (cmdr.Cmdr)

	Attributes:
	current: The current post being updated. (Post)
	local_posts: The posts coded and stored locally. (list of Post)
	new_posts: New posts from reddit, not yet coded. (list of Submission)
	post_changes: A flag for changes having been made to posts. (bool)
	reddit: A connection to Reddit. (Reddit)
	silent: A flag for suppressing postcmd text after a command. (bool)
	tag_changes: A flag for changes having been made to tags. (bool)
	update: A flag for update mode. (bool)

	Methods:
	do_list: List the specified posts. (None)
	do_quit: Leave the tracking interface. (True)
	do_tag: Add one or more tags to the current post. (None)
	do_update: Turn update mode on or off. (None)
	do_view: View a post, either by local_id or reddit_id. (None)
	list_posts: Display a list of local Post objects. (None)
	list_submissions: Display a list of Reddit Submission objects. (None)
	save_posts: Save the post data. (None)
	save_tags: Save the tag data. (None)
	update_check: Check if it is valid to update the current record. (bool)

	Overridden Methods:
	postcmd
	postloop
	preloop
	"""

	aliases = {'ls': 'list', 'q': 'quit', 't': 'tag', 'u': 'update', 'v': 'view'}
	prompt = 'tracker >> '
	word_re = re.compile('\w+')

	def do_list(self, arguments):
		"""
		List the specified posts. (ls)

		Arguments include:
			new: List the new posts that have not be coded.
		"""
		arguments = arguments.lower()
		if arguments == 'new':
			self.list_submissions(self.new_posts)
		else:
			data = [self.local_posts[post_id] for post_id in range(1, Post.num_posts + 1)]
			# Eventually there will be filters here.
			self.list_posts(data[:25])

	def do_note(self, arguments):
		"""
		Add a note to the current post. (n)
		"""
		if self.update_check():
			self.current.add_note(arguments)
			self.post_changes = True

	def do_quit(self, arguments):
		"""
		Leave the tracking interface. (q)

		The quit command accepts no-save or ns as an argument. The no-save argument
		prevents overwriting of the data files.
		"""
		if arguments.lower() in ('ns', 'no-save'):
			self.post_changes = False
			self.tag_changes = False
		self.silent = True
		return True

	def do_save(self, arguments):
		"""
		Save any changed data. (s)

		Use the 'force' or 'f' argument to force saving the data, even if the system
		doesn't think it has changed.
		"""
		force = arguments.lower() in ('f', 'force')
		if self.post_changes or force:
			self.save_posts()
			print('Post data saved.')
			self.post_changes = False
		if self.tag_changes or force:
			self.save_tags()
			print('Tag data saved.')
			self.tag_changes = False

	def do_scan(self, arguments):
		"""
		Scan another subreddit for potential articles.

		The first argument should be the name of the subreddit (no spaces). A second
		argument is allowed, it should be the number of records to check (defaults
		to 100).
		"""
		# parse the arguments.
		args = arguments.split()
		if len(args) == 1:
			# default limit.
			args.append(100)
		elif len(args) > 2:
			# invalid number of arguments.
			print('The scan command takes one or two arguments.')
			return False
		else:
			# parse limit
			try:
				args[1] = int(args[1])
			except ValueError:
				print(f'Invalid number of records: {args[1]}.')
				return False
		sub_name, limit = args
		# Get the subreddit.
		try:
			sub = self.reddit.subreddit(sub_name)
			# Get the posts with a keyword in the title.
			matches = []
			for post in sub.new(limit = limit):
				match = self.keywords.intersection(self.word_re.findall(post.title))
				if match:
					matches.append((len(match), post))
			# Sort and display by the number of keyword matches.
			if matches:
				matches.sort(key = lambda m: (m[0], m[1].title), reverse = True)
				self.list_submissions([post for match, post in matches])
			else:
				# Note that their were no matches.
				print('No articles were found with keywords in the title.')
		except praw.exceptions.PRAWException:
			# Notify about PRAW Errors.
			print('Error connecting to the subreddit.')
			print('Either the subreddit is invalid or access was denied.')

	def do_tag(self, arguments):
		"""
		Add one or more tags to the current post. (t)
		"""
		if self.update_check():
			tags = arguments.lower().split()
			for tag in tags:
				added = self.current.add_tag(tag)
				if not added:
					suggested = self.current.suggest_tags(tag)
					print('The tag {!r} was not recognized. Suggested tags:'.format(tag))
					for maybe_index, maybe_tag in enumerate(suggested, start = 1):
						print('   {}. {}'.format(maybe_index, maybe_tag))
					choice = input('Enter f to force tag, s to skip tag, or # to use suggested tag: ')
					if choice.lower() == 'f':
						self.current.add_tag(tag, force = True)
						self.tag_changes = True
					elif choice.isdigit():
						self.current.add_tag(suggested[int(choice) - 1])
						self.tag_changes = True
					elif choice.lower() == 's':
						pass
					else:
						print('Your choice was not recognized, so the tag was skipped.')
				else:
					self.tag_changes = True

	def do_update(self, arguments):
		"""
		Turn update mode on or off. (u)

		The default is to turn it on. An argument of off, false, or 0 will turn
		update mode off.
		"""
		if arguments.lower() in ('off', 'false', 'f', '0'):
			self.update = False
			text = 'off'
		else:
			self.update = True
			text = 'on'
		print('Update mode is {}.'.format(text))

	def do_view(self, arguments):
		"""
		View a post, either by local_id or reddit_id. (v)

		If the argument is next (or n), the view is shifted to the next new
		submission (on Reddit but not coded locally).
		"""
		if arguments.isdigit():
			key = int(arguments)
		elif arguments.lower() in ('n', 'next'):
			if self.new_posts:
				new_post = Post(self.new_posts.pop())
				self.local_posts[new_post.post_id] = new_post
				self.local_posts[new_post.reddit_id] = new_post
				self.post_changes = True
				key = new_post.reddit_id
			else:
				print('There are no more new posts to view.')
				return False
		elif arguments:
			key = arguments
		else:
			key = self.current.reddit_id
		try:
			post = self.local_posts[key]
		except KeyError:
			print('Invalid record ID.')
		else:
			print(post.details())
			self.current = post

	def list_posts(self, posts):
		"""
		Display a list of local Post objects. (None)

		Parameters:
		posts: The data to display. (list of Post)
		"""
		for post in posts:
			print(post)

	def list_submissions(self, submissions):
		"""
		Display a list of Reddit Submission objects. (None)

		Parameters:
		submissions: The data to display. (list of praw.Submission)
		"""
		text = '{}  {:<16}  {:<8}  {:<36}  {:>4}'
		for post in submissions:
			date_text = dt.datetime.fromtimestamp(post.created_utc).strftime('%m/%d/%y')
			print(text.format(post.id, str(post.author), date_text, post.title[:36], post.score))

	def postcmd(self, stop, line):
		"""
		Processing done after a command is handled. (bool)

		Parameters:
		stop: A flag for stopping execution of the interface. (bool)
		line: The last command from the user. (str)
		"""
		if self.silent:
			self.silent = False
		elif self.update:
			print()
			if self.current:
				print(self.current.details())
			else:
				print('No record is selected at this time (use view command).')
		else:
			print()
			print(self.status())
		return stop

	def postloop(self):
		"""
		Processing done before the application is closed. (None)
		"""
		self.do_save('')
		print('Have a nice day.')

	def preloop(self):
		"""
		Processing done when the application is started. (None)
		"""
		print('\nWelcome to the r/CriminalJusticeReform tracking application.')
		self.silent = False
		self.post_changes = False
		self.tag_changes = False
		self.current = None
		self.update = False
		print('\nAccessing Reddit ...')
		self.reddit = load_reddit()
		print('Loading stored data ...')
		self.local_posts = load_local()
		self.keywords = load_keywords()
		print('Loading Reddit data ...')
		self.new_posts = check_cjr(self.reddit, current = self.local_posts)
		print(self.status())
		print()

	def save_posts(self):
		"""Save the post data. (None)"""
		with open('post_data.txt', 'w') as post_file:
			post_file.write('post_id\tred_id\tdate\tsource\tposter\ttitle\tscore\tper\tcom\tnotes\n')
			for post_id in range(1, len(self.local_posts) // 2 + 1):
				post = self.local_posts[post_id]
				post_file.write(post.data_line())

	def save_tags(self):
		"""Save the tag data. (None)"""
		with open('tag_data.txt', 'w') as tag_file:
			tag_file.write('post_id\ttag\n')
			for post_id in range(1, len(self.local_posts) // 2 + 1):
				post = self.local_posts[post_id]
				tag_file.write(post.tag_lines())

	def status(self):
		"""
		Generate status text for the system. (str)
		"""
		lines = ['It is now {}.'.format(dt.datetime.now())]
		lines.append('There are {} records in the local post data.'.format(len(self.local_posts) // 2))
		lines.append('      and {} records in the new post data.'.format(len(self.new_posts)))
		up_text = 'on' if self.update else 'off'
		lines.append('Update mode is {}.'.format(up_text))
		return '\n'.join(lines)

	def update_check(self):
		"""
		Check if it is valid to update the current record. (bool)
		"""
		if not self.update:
			print('Update mode must be on to modify records.')
		elif not self.current:
			print('There is no record currently selected (use view command).')
		else:
			return True

def check_cjr(reddit, current = {}, verbose = False):
	"""
	Check for new posts in r/CriminalJusticeReform. (list of praw.Submission)

	Parameters:
	current: The current posts that should be ignored. (dict of str: Post)
	reddit: A reddit instance. (praw.Reddit)
	"""
	true_new = []
	cjr = reddit.subreddit('CriminalJusticeReform')
	for post in cjr.new():
		if dt.datetime.fromtimestamp(post.created_utc) < DATA_START:
			break
		if verbose:
			print('{}  {:<20}  {}'.format(post.id, str(post.author)[:20], post.title[:32]))
		if post.id in current:
			current[post.id].update(post)
		else:
			true_new.append(post)
	if not verbose:
		print()
	return true_new

def levenshtein(text_a, text_b):
	"""
	Determine the Levenshtein distance between two strings. (int)

	Parameters:
	text_a: The first string. (str)
	text_b: The second string. (str)
	"""
	# Initialize the matrix.
	matrix = [[0] * (len(text_a) + 1) for row in range(len(text_b) + 1)]
	matrix[0] = list(range(len(text_a) + 1))
	for y in range(len(text_b) + 1):
		matrix[y][0] = y
	# Fill the matrix of edits.
	for x in range(1, len(text_b) + 1):
		for y in range(1, len(text_a) + 1):
			base = [matrix[x - 1][y] + 1, matrix[x][y - 1] + 1]
			if text_b[x - 1] == text_a[y - 1]:
				base.append(matrix[x - 1][y - 1])
			else:
				base.append(matrix[x - 1][y - 1] + 1)
			matrix[x][y] = min(base)
	# Return the final value.
	return matrix[-1][-1]

def load_keywords():
	"""
	Load the key words for subreddit scanning. (set of str)
	"""
	keywords = set()
	with open('keywords.txt') as word_file:
		for line in word_file:
			keywords.add(line.strip())
	return keywords

def load_local():
	"""
	Load the local data. (dict)
	"""
	posts = {}
	with open('post_data.txt') as post_file:
		for line in post_file:
			if line.startswith('post_id'):
				continue
			new_post = Post(line)
			posts[new_post.post_id] = new_post
			posts[new_post.reddit_id] = new_post
	with open('tag_data.txt') as tag_file:
		for line in tag_file:
			if line.startswith('post_id'):
				continue
			post_id, tag = line.strip().split('\t')
			posts[int(post_id)].add_tag(tag, force = True)
	return posts

def load_reddit(read_only = False, **kwargs):
	"""
	Load a Reddit instance. (praw.Reddit)

	Parameters:
	read_only: A flag for making a read only instance. (bool)
	kwargs: Key-word arguments for the Reddit instance. (bool)
	"""
	access = ACCESS_KWARGS.copy()
	access.update(kwargs)
	reddit = praw.Reddit('main_user', **access)
	return reddit

if __name__ == '__main__':
	tracker = Tracker()
	tracker.cmdloop()