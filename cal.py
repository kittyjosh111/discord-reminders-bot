#!/usr/bin/python3
# Discord bot that serves as a to-do application
# Creates daily to-do lists and sends reminders every X hours
# Can be communicated with to create new tasks with
# varying categories, and be marked done/not done through chat.
# Tasks are saved as a list of dicts to a file, named by MM-DD-YYYY
# Each new day, a new task list is created and saved.
#
# Also, a template file can be made. It takes in a list of
# day, content. When creating a new daily list, we look through the template
# and pre-fill that day's list with predefined tasks.
#
# A task should look like this:
# [ [id, [{"content": content}, {"status": status}]] ]
# Basically, a list whose index 0 is an ID, and 1 is a list of dicts


from datetime import datetime as dt
import json
import os
import copy
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

def list_write(filename, list):
  """Function to save LIST (list) that is passed in to a FILENAME (string).
  If the file already exists, its content is overwritten. Returns LIST"""
  with open(filename, 'w') as save: #w is overwrite
     save.write(json.dumps(list))
  return list #returns in case we want to reuse this somewhere

def list_read(filename):
  """Function to read FILENAME and return the list inside"""
  with open(filename) as read:
    return json.load(read) #return contents with their correct type

def get_time(arg):
  """Function to get details of the current date and time.
  Takes in ARG, wihch is a string argument. Essentially
  a wrapper for strftime"""
  # get_time("%m-%d-%Y") -> '01-01-2021' (date)
  # ..."%A" -> 'Monday' (day)
  # ..."%H" -> '09' (hour)
  # ..."%M" -> '30' (minute)
  return dt.now().strftime(arg)

def get_task():
  """Function to read tasks list from storage"""
  now_date = get_time("%m-%d-%Y")
  return list_read(now_date)

def create_task(list, content, status=0):
  """Function that creates a task. Takes in a CONTENT (string), STATUS (string)).
  Status (0 for not done, 1 for done) defaults to 0."""
  if list: #nonempty list
    id = max(list)[0] + 1
  else: #empty list
    id = 0 #start the ids from 0
  return list + [ [id, [{"content": content}, {"status": status}]] ]

def delete_task(list, id):
  """Function to delete the task correlated to id ID in task list"""
  list_copy = list[:] #create a copy
  for sublist in list_copy: #loop through each individual sublist
    if sublist[0] == id: #ids should be the first item in the list
      list_copy.remove(sublist) #delete
  if list == list_copy:
    return None #nothing changed
  return list_copy #return what we have left

def edit_attr(list, id, key, edit):
  """Function that checks for task with ID in LIST,
  then change the value given a KEY for the dictionary.
  This is done by passing in a function to EDIT."""
  list_copy = copy.deepcopy(list) #need to do a deep copy to handle nested dicts
  for sublist in list_copy: #loop through each individual sublist
    if sublist[0] == id: #ehck the ids
      for dict in sublist[1]: #then loop through the dicts
        if key in dict: #finding the key
          dict[key] = edit(dict[key]) #run edit() on the value
  if list == list_copy:
    return None #nothing changed
  return list_copy #return what we have left

def toggle_status(list, id):
  """Function to toggle a task as done (1) or not done (0)"""
  return edit_attr(list, id, 'status', lambda x: 1 if x == 0 else 0) #lambda toggles 0 and 1

def edit_task(list, id, key, value):
  """Function to change the VALUE of a KEY of a task"""
  return edit_attr(list, id, key, lambda x: value) #lambda just returns VALUE

def create_template(date, tasks):
  """Function that takes in a list of TASKS to create for a DATE template.
  TASKS should be a list of the content of the tasks you want."""
  assert date == 'Sunday' or date == 'Monday' or date == 'Tuesday' or date == 'Wednesday' or date == 'Thursday' or date == 'Wednesday' or date == 'Thursday' or date == 'Friday' or date == 'Saturday', 'date should be a day of the week (Monday, Tuesday, etc.)'
  if os.path.isfile(date): #make sure we have a file
    template_list = list_read(date)
  else:
    template_list = [] #init a blank list
  for each in tasks: #iterate over the list TASKS
    template_list = create_task(template_list, each) #keep appending
  return list_write(date, template_list) #write it to disk as DATE

def edit_template(date, id, key, value):
  """Function to read a template, edit it, then save it.
  Takes in DATE, which is the name of the template, ID
  of the task, KEY and VALUE to replace"""
  if os.path.isfile(date):
    return edit_task(list_read(date), id, key, value) #call edit_task

def delete_template(date, id):
  """Function to read a template, then delete task ID from it."""
  if os.path.isfile(date):
    return delete_task(list_read(date), id) #call delete_task, return the edited list

def make_text(list):
  """Function to make a more human-readable output of the task LIST"""
  text = '' #init a blank string
  if not list:
    return 'No tasks found!\n' #saves from executing below
  for each in list:
    id = each[0] #get id
    content = None #preset these
    status = None
    for dict in each[1]: #then loop through the dicts
      if 'content' in dict: #finding the content
        content = dict['content']
      elif 'status' in dict: #and now the status
        if not dict['status']:
          status = 'x' #x mark
        else:
          status = '✓' #check mark
      if content and status: #when we get both
        text += f"[{status}] {content} - (ID: {id})\n" #add them to string
  return text

def init_tasks():
  """Function that returns a string showing what tasks there are to do, along with their status"""
  curr_day = get_time("%A") #Monday, Tuesday, etc.
  curr_date = get_time("%m-%d-%Y") #01/01/2021, etc.
  #this logic loop will not append templates if they were created after the curr_date list.
  #run load_template to do so
  if not os.path.isfile(curr_date): #the current daily list is nonexistent
    print("DEBUG: Daily list non existent. Creating...")
    if os.path.isfile(curr_day): #then, if a template exists
      print("DEBUG: Template for today was found. Adding to daily list...")
      task_list = list_read(curr_day) #first stick in the template
    else:
      task_list = [] #just make an empty list
    list_write(curr_date, task_list) #save
  else:
      task_list = list_read(curr_date) #load normally
  text = make_text(task_list)
  return f"Here is your list of tasks to complete today:\n\n{text}"

def load_template():
  """Function that loads in a template if today's task list was created before the template was.
  First creates an empty list using the new template, then loops through the existing task list
  and appends it to the list. Saves this all back into the daily list.
  Returns a string of text as a message."""
  curr_day = get_time("%A") #Monday, Tuesday, etc.
  curr_date = get_time("%m-%d-%Y") #01/01/2021, etc.
  if os.path.isfile(curr_date) and os.path.isfile(curr_day):
    new_list = list_read(curr_day)
    if new_list == []:
      return f"Template {curr_day} is empty. No action taken."
    else:
      for each in list_read(curr_date):
        dicts_list = each[1]
        id = max(new_list)[0] + 1
        new_list = new_list + [ [id, dicts_list] ]
      list_write(curr_date, new_list)
      return f"Daily task list had been edited to include tasks from the template for {curr_day}."
  else:
    return 'Missing either the template or daily tasks list.'  #load_template was called when certain requirements were not met

### Discord bot portion ###

load_dotenv()
intents = discord.Intents().all()
client = commands.Bot(command_prefix=',', intents=intents)

def start(discord_bot_token, notifications_channel, notifications_frequency, start_time, end_time, blacklist=[]):
    """Function to start the discord bot portion.
    The task_loop needs NOTIFICATIONS_CHANNEL to know which channel to write to, and the
    NOTIFICATIONS_FREQUENCY (in seconds) to know how frequently to send messages.
    START_TIME tells the bot when to start NOT sending messages,
    END_TIME tells the bot when to end NOT sending messages. Basically, the bot will silence itself from [START_TIME, END_TIME].
        For example, START_TIME = 1 and END_TIME = 6 blocks the bot from messaging you during the period of 1 - 6 AM.
    BLACKLIST prevents messages from being read from other channels in a server.
    DISCORD_BOT_TOKEN is used to start the bot."""

    @tasks.loop(seconds=notifications_frequency)
    async def task_loop():
        hour = int(get_time("%H")) #gets the hour only
        channel = client.get_channel(int(notifications_channel))
        if hour >= start_time and hour <= end_time:
            print(f"DEBUG: Loop triggered in {channel}. If you see None there, something is wrong.\nThe hour is {hour}, and thus a message was not sent.")
        else:
            print(f"DEBUG: Loop triggered in {channel}. If you see None there, something is wrong.\nThe hour is {hour}, and thus a message was sent.")
            await channel.send(f"This is a reminder message. {init_tasks()}")

    @client.event
    async def on_ready():
        task_loop.start()
        print('Online. blacklisted channel IDs:', blacklist)

    @client.event
    async def on_message(message):
        def check(message):
            return message.author == message.author and message.channel == message.channel and not message.author.bot
        if str(message.channel.id) not in blacklist:
            if message.author == client.user or message.author.bot:
                return
            print("DEBUG: Message Received:", message.content)
            curr_date = get_time("%m-%d-%Y") #check if we need a new daily list
            if not os.path.isfile(curr_date):
                init_tasks() #if so, then create
            if 'help' in message.content:
                response = "Commands available to manage tasks are 'create_task', 'edit_task', 'delete_task', 'show_tasks', and 'toggle_status'."
                response += "\n- 'create_task' or '.cta' allows you to create daily tasks by providing their descriptions."
                response += "\n- 'edit_task' of '.eta' allows you to edit pre-existing daily tasks by overwriting their descriptions."
                response += "\n- 'delete_task' or '.dta'  allows you to delete pre-existing daily tasks."
                response += "\n- 'show_task' or '.sta' allows you to view all daily tasks, as well as their statuses."
                response += "\n- 'toggle_status' or '.ts' allow you to toggle the status of a pre-existing daily task between done (✓) or not done (x)."
                response += "\n\nCommands to edit templates include 'create_template', 'edit_template', 'delete_template', 'show_template', and 'load_template'."
                response += "\n- 'create_template' or '.cte' allows you to create or add tasks to a template for a specific day of the week by providing their descriptions."
                response += "\n- 'edit_template' or '.ete' allows you to edit pre-existing template tasks by overwriting their descriptions."
                response += "\n- 'delete_template' or '.dte' allows you to delete pre-existing template tasks."
                response += "\n- 'show_template' or '.ste' allows you to view the templates for every day of the week."
                response += "\n- 'load_template' or '.lte' allows you to load in the tasks from a template, if you have already created your daily task beforehand."

            elif 'show_task' in message.content or '.sta' in message.content:
                response = init_tasks()
            elif 'create_task' in message.content or '.cta' in message.content:
                await message.channel.send("Please enter the description of the task you want to add. To add multiple tasks, separate each entry with a semi-colon. Ex: Wake up; Eat breakfast; etc.") #wait for further input
                user_input = await client.wait_for('message', check=check)
                tasks_list = user_input.content.split("; ")
                response = ""
                for each in tasks_list:
                    list_write(curr_date, create_task(list_read(curr_date), each)) #write to disk
                    response += f"\nTask with description '{each}' has been created."
                response += f"\n\nYour current list of tasks is as follows:\n\n{make_text(list_read(curr_date))}"
            elif 'delete_task' in message.content or '.dta' in message.content:
                curr_list = list_read(curr_date)
                if curr_list:
                    await message.channel.send(make_text(curr_list))
                    await message.channel.send("Please enter the ID number of the task you want to delete. To delete multiple tasks, separate each id with a semi-colon. Ex: 1; 2; 3; etc.") #wait for user input
                    user_input = await client.wait_for('message', check=check)
                    id_list = user_input.content.split("; ")
                    response = ""
                    for each in id_list:
                        if each.isdigit(): #ensure its a digit
                            precheck = delete_task(list_read(curr_date), int(each)) #make sure this command doesnt fail
                            if precheck or precheck == []: #kinda need to be able to interpret a blank list
                                list_write(curr_date, precheck) #write to disk
                                response += f"\nTask with id {each} has been deleted."
                            else:
                                response += f"\nTask with id {each} was not found. No action was taken."
                        else:
                            response += f"\nTask id must be a number."
                    response += f"\n\nYour current list of tasks is as follows:\n\n{make_text(list_read(curr_date))}"
                else:
                    response = "The tasks list is empty or nonexistent. Create one now using 'create_tasks'."
            elif 'edit_task' in message.content or '.eta' in message.content:
                curr_list = list_read(curr_date)
                if curr_list:
                    await message.channel.send(make_text(curr_list))
                    await message.channel.send("Please enter the ID number of the task you want to edit.") #get first user input
                    user_input_id = await client.wait_for('message', check=check)
                    if user_input_id.content.isdigit(): #make sure id is a digit
                        await message.channel.send(f"Please enter the new description for task number {user_input_id.content}.") #then the second
                        user_input_str = await client.wait_for('message', check=check)
                        precheck = edit_task(list_read(curr_date), int(user_input_id.content), 'content', str(user_input_str.content)) #make sure this doesnt fail
                        if precheck:
                            list_write(curr_date, precheck) #write to disk
                            response = f"Task with id {user_input_id.content} has been edited to '{user_input_str.content}'."
                            response += f"\n\nYour current list of tasks is as follows:\n\n{make_text(list_read(curr_date))}"
                        else:
                            response = f"Task with id {user_input_id.content} was not found. No action was taken."
                    else:
                        response = f"Task id must be a number."
                else:
                    response = "The tasks list is empty or nonexistent. Create one now using 'create_tasks'."
            elif 'toggle_status' in message.content or '.ts' in message.content:
                await message.channel.send(make_text(list_read(curr_date)))
                await message.channel.send("Please enter the ID number of the task you want to change the status of.") #wait for user input
                user_input = await client.wait_for('message', check=check)
                if user_input.content.isdigit(): #ensure its a digit
                    precheck = toggle_status(list_read(curr_date), int(user_input.content)) #make sure this command doesnt fail
                    if precheck: #kinda need to be able to interpret a blank list
                        list_write(curr_date, precheck) #write to disk
                        response = f"Task with id {user_input.content} has had its status toggled."
                        response += f"\n\nYour current list of tasks is as follows:\n\n{make_text(list_read(curr_date))}"
                    else:
                        response = f"Task with id {user_input.content} was not found. No action was taken."
                else:
                    response = f"Task id must be a number."
            elif 'create_template' in message.content or '.cte' in message.content:
                await message.channel.send("Please enter the day you want to create a template for.\nDays accepted include Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, or Saturday.") #wait for further input
                user_input_day = await client.wait_for('message', check=check)
                if user_input_day.content in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
                    await message.channel.send(f"Please enter a list of task description separated by semi-colons. Ex: Wake up; Eat breakfast; Go to sleep.")
                    user_input_tasks = await client.wait_for('message', check=check)
                    tasks_list = user_input_tasks.content.split("; ")
                    create_template(user_input_day.content, tasks_list)
                    response = f"Template for day {user_input_day.content} created. It will automatically apply the next time it is {user_input_day.content}. If the template you created is for today, run 'load_template' to add the tasks to today's task list."
                    response += f"\n\nThe template's list of tasks is as follows:\n\n{make_text(list_read(user_input_day.content))}"
                else:
                    response = "Input does not match one of the valid days."
            elif 'delete_template' in message.content or '.dte' in message.content:
                await message.channel.send("Please enter the day's template you want to edit.\nDays accepted include Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, or Saturday.") #wait
                user_input_day = await client.wait_for('message', check=check)
                if user_input_day.content in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
                    if os.path.isfile(user_input_day.content) and list_read(user_input_day.content): #make sure the template actually exists and has content
                         await message.channel.send(make_text(list_read(user_input_day.content)))
                         await message.channel.send(f"Please enter the id of the task you wish to delete. To delete multiple tasks, separate each id with a semi-colon. Ex: 1; 2; 3; etc.")
                         user_input_id = await client.wait_for('message', check=check)
                         response = ""
                         for each in user_input_id.content.split("; "):
                             if each.isdigit(): #ensure its a digit
                                 precheck = delete_template(user_input_day.content, int(each))
                                 if precheck or precheck == []: #kinda need to be able to interpret a blank list
                                     list_write(user_input_day.content, precheck)
                                     response += f"\nTemplate for day {user_input_day.content} edited. Task with id {each} is removed."
                                 else:
                                     response += f"\nTask with id {each} was not found. No action was taken."
                             else:
                                 response += "\nTask id must be a number."
                         response += f"\n\nThe template's list of tasks is as follows:\n\n{make_text(list_read(user_input_day.content))}"
                    else:
                        response = f"A template for {user_input_day.content} does not exist or is blank. Create one by typing 'create_template'."
                else:
                    response = "Input does not match one of the valid days."
            elif 'edit_template' in message.content or '.ete' in message.content:
                await message.channel.send("Please enter the day's template you want to edit.\nDays accepted include Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, or Saturday.") #wait
                user_input_day = await client.wait_for('message', check=check)
                if user_input_day.content in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
                    if os.path.isfile(user_input_day.content) and list_read(user_input_day.content): #make sure the template actually exists and has content
                         await message.channel.send(make_text(list_read(user_input_day.content)))
                         await message.channel.send(f"Please enter the id of the task you wish to edit.")
                         user_input_id = await client.wait_for('message', check=check)
                         if user_input_id.content.isdigit(): #ensure its a digit
                             await message.channel.send(f"Please enter the new description for task number {user_input_id.content}.")
                             user_input_value = await client.wait_for('message', check=check)
                             precheck = edit_template(user_input_day.content, int(user_input_id.content), 'content', str(user_input_value.content))
                             if precheck or precheck == []: #kinda need to be able to interpret a blank list
                                 list_write(user_input_day.content, precheck)
                                 response = f"Template for day {user_input_day.content} edited. Task with id {user_input_id.content} has been edited."
                                 response += f"\n\nThe template's list of tasks is as follows:\n\n{make_text(list_read(user_input_day.content))}"
                             else:
                                 response = f"Task with id {user_input_id.content} was not found. No action was taken."
                         else:
                             response = "Task id must be a number."
                    else:
                        response = f"A template for {user_input_day.content} does not exist or is blank. Create one by typing 'create_template'."
                else:
                    response = "Input does not match one of the valid days."
            elif 'load_template' in message.content or '.lte' in message.content:
                response = load_template()
                response += f"\n\nYour current list of tasks is as follows:\n\n{make_text(list_read(curr_date))}"
            elif 'show_template' in message.content or '.ste' in message.content:
                response=""
                for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
                    if os.path.isfile(day):
                        precheck = list_read(day)
                        if precheck != []:
                            response += f"\n- {day}:\n{make_text(precheck)}"
                        else:
                            response += f"\n- Template file for {day} is blank.\nCreate some tasks using 'create_template'.\n"
                    else:
                        response += f"\n- No template file for {day}.\nCreate some tasks using 'create_template'.\n"
            else:
                return #ignore anything else
            await message.channel.send(response) #send out the response
        else:
            print("DEBUG: Message received in a blacklisted channel. Ignoring.")

    client.run(discord_bot_token)

### Example way to start the bot

start(os.getenv('DISCORD_API_KEY'), os.getenv('NOTIFICATIONS'), 1800, 1, 6, os.getenv('BLACKLIST'))
