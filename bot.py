import os
import asyncio
import re
import requests
import discord
import shelve
from pathlib import Path
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from secret import token

with open("secret.key","rb") as fd:
    key=fd.read()

f=Fernet(key)

TOKEN = token
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
# unameDict = {}
browserSesion = {}

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command()
async def login(ctx, uname, pswd):
    path=Path(str(ctx.author))
    if not path.exists():
        os.mkdir(str(ctx.author))
        with shelve.open(Path(str(ctx.author),"data.db")) as shelveFile:
            shelveFile["username"]=uname
            encryptPsswd=f.encrypt(pswd.encode())
            shelveFile["password"]=encryptPsswd
        await ctx.send("Log in successfull")
        await ctx.send("Login details stored successfully")
        return 
    else:
        with shelve.open(Path(str(ctx.author),"data.db")) as shelveFile:
            shelveFile["username"]=uname
            encryptPsswd=f.encrypt(pswd.encode())
            shelveFile["password"]=encryptPsswd
        await ctx.send("Already logged in. Login details have been replaced ")
        return

@bot.command()
async def startLMS(ctx):
    path=Path(str(ctx.author),"data.db.dat")
    if not path.exists():
        await ctx.send("Login first")
        return
    
    #to do take browser from dict
    if str(ctx.author) in browserSesion:
        await ctx.send("Already done")
        return
    else:
        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Firefox(options=options)
        browserSesion[str(ctx.author)]=browser
    browser.get("https://lmsug23.iiitkottayam.ac.in/login/index.php")
    
    uname = browser.find_element(By.ID, "username")
    psswd = browser.find_element(By.ID, "password")
    btn = browser.find_element(By.ID, "loginbtn")
    path=Path(str(ctx.author),"data.db")
    with shelve.open(path) as fd:
        uname.send_keys(fd["username"])
        decryptPsswd=f.decrypt(fd["password"]).decode()
        psswd.send_keys(decryptPsswd)
    btn.click()
    
    browser.get("https://lmsug23.iiitkottayam.ac.in/calendar/export.php?")
    events = browser.find_element(By.ID, "id_events_exportevents_all")
    timeperiod = browser.find_element(By.ID, "id_period_timeperiod_recentupcoming")
    events.click()
    timeperiod.click()
    
    btn = browser.find_element(By.ID, "id_generateurl")
    btn.click()
    url = browser.find_element(By.ID, "calendarexporturl").get_attribute("value")
    #browser.quit() #check if req later also when remove val may be still in dict chech that to
    await ctx.send("Calendar URL generated, monitoring changes...")
    asyncio.create_task(check_calendar_change(ctx, url))

@bot.command()
async def stopLMS(ctx):

    if str(ctx.author) in browserSesion:
        browser=browserSesion[str(ctx.author)]
        del browserSesion[str(ctx.author)]
        browser.quit()
        await ctx.send("Done")
    else:
        await ctx.send("Did not startLMS to stop it")
            
    
def download_calendar(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
    except requests.RequestException as e:
        print(f"Error downloading the calendar: {e}")
    return None

def extract_event_details(content):
    dtend_list = re.findall(r"DTEND(?:;TZID=[^:]+)?:(\d{8}T\d{6}Z)", content)
    summary_list = re.findall(r"SUMMARY:(.+)", content)
    return {summary: dtend for summary, dtend in zip(summary_list, dtend_list)}

def convert_utc_to_ist_with_tzid(utc_str):
    utc_dt = datetime.strptime(utc_str, "%Y%m%dT%H%M%SZ")
    ist_dt = utc_dt + timedelta(hours=5, minutes=30)
    return ist_dt

def remove_dtstamp(content):
    return re.sub(r"^DTSTAMP:.*\n?", "", content, flags=re.MULTILINE)

async def check_calendar_change(ctx, url):
    base_dir=Path(str(ctx.author))
    prev_filename = base_dir/"previous_calendar.ics"
    new_filename = base_dir/"new_calendar.ics"

    while True:
        new_calendar = download_calendar(url)
        if new_calendar:
            new_calendar = remove_dtstamp(new_calendar)
            write_to_ics(new_calendar, new_filename)

            if os.path.exists(prev_filename):
                # Compare the previous and new calendar files
                if compare_files(prev_filename, new_filename):
                    # Files are identical, no changes, skip further processing
                    os.remove(new_filename)
                else:
                    # Files differ, process changes
                    with open(prev_filename, "r") as prev_file:
                        prev_content = prev_file.read()
                        previous_events = extract_event_details(prev_content)

                    new_events = extract_event_details(new_calendar)
                    new_events={key.rstrip("\r"):value for (key,value) in new_events.items()}
                    # print(new_events)
                    # Using set operations to find added and removed events
                    previous_set = set(previous_events.keys())
                    new_set = set(new_events.keys())
                    # new_set={element.replace("\r","") for element in new_set}
                    # print(previous_set)
                    # print(new_set)
                    added_events = new_set - previous_set
                    removed_events = previous_set -new_set
                    print(f"Added events{added_events}")
                    # Create message for added events
                    added_messages = [
                        f"New event: {summary}\nDue by: {convert_utc_to_ist_with_tzid(new_events[summary]).strftime('%Y-%m-%d %H:%M:%S')} IST"
                        for summary in added_events if "Attendance" not in summary
                    ]

                    # Create message for removed events
                    removed_messages = [
                        f"Event: {summary} removed"
                        for summary in removed_events if "Attendance" not in summary
                    ]

                    # Send messages
                    if added_messages:
                        await ctx.send("\n".join(added_messages))
                    if removed_messages:
                        await ctx.send("\n".join(removed_messages))

                    # Replace the old calendar with the new one
                    os.remove(prev_filename)
                    os.rename(new_filename, prev_filename)
            else:
                # First run, save the new calendar as the previous one
                os.rename(new_filename, prev_filename)

        await asyncio.sleep(10)
        
def compare_files(file1, file2):
    """Compare two files line by line."""
    with open(file1, "r") as f1, open(file2, "r") as f2:
        return f1.read() == f2.read()

def write_to_ics(content, filename):
    with open(filename, "w") as f:
        f.write(content)

@bot.command()
async def due_events(ctx):
    prev_filename = "previous_calendar.ics"
    
    if not os.path.exists(prev_filename):
        await ctx.send("No calendar data available.")
        return
    
    with open(prev_filename, "r") as f:
        calendar_content = f.read()
    
    events = extract_event_details(calendar_content)
    current_time = datetime.now() + timedelta(hours=5, minutes=30)

    due_events = []
    for summary, dtend in events.items():
        if "Attendance" in summary:
            continue
        
        ist_time = convert_utc_to_ist_with_tzid(dtend)
        if current_time <= ist_time:
            due_events.append(f"Event: {summary}\nDue by: {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST")
    
    if due_events:
        await ctx.send("\n\n".join(due_events))
    else:
        await ctx.send("No due events at the moment.")

bot.run(TOKEN)
