from flask import Blueprint, redirect, request, render_template, url_for, flash, current_app
import requests
import json
import os
import re
import pycountry
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from f1.driver_forms import CreateForm, SearchForm, EditForm
from flask_login import current_user, login_required
from roles.permissions import admin_permission
from sql.db import DB
f1 = Blueprint('f1', __name__, url_prefix='/', template_folder="templates")

# sr2484 | Apr 22
def get_api():
  """Method to provide api endpoint details"""
  api_val = {}
  print(current_app)
  api_val["driver_url"] = "https://api-formula-1.p.rapidapi.com/drivers"
  api_val["headers"] = {
    "X-RapidAPI-Key": current_app.api_key,
    "X-RapidAPI-Host": current_app.api_host
  }
  print("api value from current_app")
  print(current_app.api_key)
  print(api_val)
  return api_val

# sr2484 | Apr 22
def get_drivers():
  """
    Method that gets driver information from database and API Endpoints
    Works currently with range specifications. 
    Need to update based on search query
  """
  drivers = []
  api_val = get_api()
  try:
    for i in range(1, 21):
      result = DB.selectAll("SELECT response, name FROM IS601_f1_drivers where id = %s", i)
      print(result.status)
      if result.status and (result.rows or result.row):
        response = json.loads(str(result.rows[0]['response']))
        driver = {}
        driver["url"] = response[0]["image"]
        driver["name"] = result.rows[0]['name']
        drivers.append(driver)
        print(drivers)
      else:
        print("Get data from url")
        querystring = {"id":str(i)}
        response = requests.request("GET", api_val["driver_url"], headers=api_val["headers"], params=querystring)
        if response.status_code == 200:
          jsonresponse = json.loads(response.text)
          for item in jsonresponse["response"]:
            dri = {}
            for i in item:
              if i == "image":
                dri["url"] = item[i]
                drivers.append(dri)
              elif i == "name":
                dri["name"] = item[i]

          result = DB.insertOne("INSERT INTO IS601_f1_drivers (id, name, response) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE name = %s, response = %s",
                                jsonresponse["response"][0]["id"], jsonresponse["response"][0]["name"], 
                                json.dumps(jsonresponse["response"]), jsonresponse["response"][0]["name"], 
                                json.dumps(jsonresponse["response"]))
          if result.status:
            drivername = jsonresponse["response"][0]["name"]
            print(f"Added driver {drivername}")
        else:
          print(f"Error: {response}")
          print(response.text)
          return drivers
    return drivers
  except Exception as e:
    print(e)
    flash("Error getting driver data", "danger")

# sr2484 |Apr 24
@f1.route("/add-driver", methods=["GET","POST"])
@login_required
def add_driver():
  driverid = request.form.get("driverid", None)
  args = {**request.args}
  if driverid:
    try:
      result = DB.selectOne(f"Select id, name, image, response From IS601_f1_drivers where id = {driverid}")
      if result.status:
        driver_name = str(driverid) + "NA"
        if result.row and result.row["image"] and result.row["name"] != driver_name:
          drivername = result.row["name"]
          flash(f"Driver {drivername} already stored", "warning")
        else:
          driver = json.loads(str(result.row["response"]))
          driver = driver[0]
          bdate = datetime.strptime(driver["birthdate"], '%Y-%m-%d').date()
          result = DB.update("Update IS601_f1_drivers SET name = %s, country = %s, birthdate = %s, podiums = %s, championships = %s, image = %s where id = %s",
                  driver["name"], driver["country"]["code"], bdate, driver["podiums"], driver["world_championships"], driver["image"], driver["id"])
          if result.status:
            drivername = driver["name"]
            flash(f"Added driver {drivername}", "success")
            result = DB.selectOne(f"Select id from IS601_f1_drivers where name like '%{drivername}%' and id >= 1000")
            if result.status and result.row:
              result = DB.delete("DELETE FROM IS601_f1_drivers WHERE id = %s", result.row["id"])
              if result.status:
                flash(f"User created record deleted for the driver {drivername}", "success")
            teamcount = 0
            for team in driver["teams"]:
              result = DB.insertOne("INSERT INTO IS601_f1_driver_stats (driver_id, seasons, teams, logo) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE teams = %s, logo = %s",
                                  driver["id"], team["season"], team["team"]["name"], team["team"]["logo"],
                                  team["team"]["name"], team["team"]["logo"])
              if result.status:
                teamcount += 1    
            if teamcount == len(driver["teams"]):
              flash(f"Extracted and updated stats of {drivername}", "success")
            else:
              flash("Driver data not extracted", "danger")
          else:
            dname = driver["name"]
            flash(f"Update failed for the driver {dname}")
    except Exception as e:
      print(f"Error: {str(e)}")
      flash("Error connecting to the server. Please contact administrator", "danger")
  return redirect(url_for("f1.create_drivers", **args))

# sr2484 | Apr 22
def search_drivers(drivername):
  """
    Method to search the drivers in the database using the drivernames
    Returns:
      Driver list that matches the driver names from backend databse
  """
  drivers = []
  args = {}
  args["drivername"] = "%"+drivername+"%"
  query = "SELECT id, name, country, birthdate, podiums, championships, image FROM IS601_f1_drivers where image is not null"
  if drivername != "":
    query += " AND name like %(drivername)s"
  try:
    result = DB.selectAll(query, args)
    if result.status and result.rows:
      for driver in result.rows:
        dri = {}
        dri["id"] = driver["id"]
        dri["name"] = driver["name"]
        dri["url"] = driver["image"]
        drivers.append(dri)
    else:
      flash("No drivers found", "warning")
  except Exception as e:
    print(f"Error: {str(e)}")
  return drivers

# sr2484 | Apr 22
def get_config_id():
  """
    Method to get id for new driver data creations from config table
  """
  id = 0
  try:
    result = DB.selectOne("SELECT create_prefix from IS601_f1_config where id = 1")
    print(result)
    if result.status:
      if result.row:
        id = int(result.row["create_prefix"])
      else:
        flash("Missing configuration data/Connection issue", "danger")
        id = 0
  except Exception as e:
    print(str(e))
    flash("Unable to access server, Please try again or contact administrator", "danger")
  return int(id)

# sr2484 | Apr 22
def update_config_id(id):
  """
    Method to update the config parameters to point to new id
  """
  try:
    result = DB.update(f"UPDATE IS601_f1_config SET create_prefix = {id} where id = 1")
    print(result)
    if result.status:
      return True
    else:
      return False
  except Exception as e:
    print(str(e))
    flash("Unable to access server, Please try again or contact administrator", "danger")

# sr2484 | Apr 23
def get_all_drivers():
  """
    Method to get all drivers from the table
  """
  try:
    result = DB.selectAll("Select id, name, country, birthdate, podiums, championships, image from IS601_f1_drivers")
    if result.status:
      return result.rows
    else:
      return []
  except Exception as e:
    print(f"Error: {str(e)}")
    flash("Unable to retrieve all records from db", "danger")

@f1.route("/update-all-drivers")
@login_required
def update_drivers():
  """
    Update driver information from API response stored in the db
  """
  args = {**request.args}
  try:
    result = DB.selectAll("Select id, response From IS601_f1_drivers where id < 1000")
    if result.status:
      print(result.status)
      for row in result.rows:
        driver = json.loads(str(row['response']))
        driver = driver[0]
        print(driver["id"])
        bdate = datetime.strptime(driver["birthdate"], '%Y-%m-%d').date()
        result = DB.update("Update IS601_f1_drivers SET country = %s, birthdate = %s, podiums = %s, championships = %s, image = %s where id = %s",
                  driver["country"]["code"], bdate, driver["podiums"], driver["world_championships"], driver["image"], driver["id"])
        if result.status:
          continue
        else:
          dname = driver["name"]
          flash(f"Update failed for the driver {dname}")
  except Exception as e:
    print(f"Error: {str(e)}")
    flash("Error connecting to the server. Please contact administrator", "danger")
  return redirect(url_for("f1.list_drivers"), **args)

# sr2484 | May 3
@f1.route("/update-one-driver")
@login_required
def update_one_driver():
  """
    Update driver information from API response stored in the db
  """
  id = request.args.get("id")
  try:
    result = DB.selectOne(f"Select id, response From IS601_f1_drivers where id = {id}")
    if result.status:
      print(result.status)
      row = result.row
      driver = json.loads(str(row['response']))
      driver = driver[0]
      print(driver)
      print(driver["id"])
      bdate = datetime.strptime(driver["birthdate"], '%Y-%m-%d').date()
      result = DB.update("Update IS601_f1_drivers SET name=%s, country = %s, birthdate = %s, podiums = %s, championships = %s, image = %s where id = %s",
                driver["name"], driver["country"]["code"], bdate, driver["podiums"], driver["world_championships"], driver["image"], driver["id"])
      if not result.status:
        dname = driver["name"]
        flash(f"Update failed for the driver {dname}")
      else:
        flash("Driver info reset successful","success")
  except Exception as e:
    print(f"Error: {str(e)}")
    flash("Error connecting to the server. Please contact administrator", "danger")
  return redirect(url_for("f1.edit_driver", id=id))

@f1.route("/insert-driver-stats")
@login_required
def insert_driver_stats():
  """
    Update driver statistics information from API response stored in the db
  """
  args = {**request.args}
  try:
    result = DB.selectAll("Select id, response From IS601_f1_drivers where id < 1000")
    if result.status:
      print(result.status)
      for row in result.rows:
        driver = json.loads(str(row['response']))
        driver = driver[0]
        print(driver["id"])
        bdate = datetime.strptime(driver["birthdate"], '%Y-%m-%d').date()
        for team in driver["teams"]:
          result = DB.insertOne("INSERT INTO IS601_f1_driver_stats (driver_id, seasons, teams, logo) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE teams = %s, logo = %s",
                                driver["id"], team["season"], team["team"]["name"], team["team"]["logo"],
                                team["team"]["name"], team["team"]["logo"])
        if result.status:
          continue
        else:
          dname = driver["name"]
          flash(f"Insert failed for the driver {dname}")
  except Exception as e:
    print(f"Error: {str(e)}")
    flash("Error connecting to the server. Please contact administrator", "danger")
  return redirect(url_for("f1.list_drivers"), **args)

# sr2484 | Apr 22
@f1.route("/drivers", methods=["GET"])
def list_drivers():
  drivers = []
  args = {}
  query = ""
  sortoptions = ["name", "country", "podiums", "championships", "favorites"]
  args["name"] = request.args.get("drivername")
  args["team"] = request.args.get("team")
  args["country"] = request.args.get("country")
  args["column"] = request.args.get("column")
  args["order"] = request.args.get("order")
  args["favs"] = request.args.get("favs")
  limit = request.args.get("limit")
  if current_user.get_id():
    query = "Select distinct id, name, country, birthdate, podiums, championships, image, IFNULL(f.fcount, 0) as favcount, IFNULL(u.userfav, 0) as userfav"
  else:
    query = "Select distinct id, name, country, birthdate, podiums, championships, image, IFNULL(f.fcount, 0) as favcount "
  query += """ from IS601_f1_drivers as d 
            LEFT JOIN IS601_f1_driver_stats as s on d.id=s.driver_id 
            LEFT JOIN (select driver_id, count(*) as fcount from IS601_f1_userfavs group by driver_id) as f on d.id=f.driver_id"""
  if current_user.get_id():
    query += f" LEFT JOIN (select driver_id, 1 as userfav from IS601_f1_userfavs where user_id={current_user.get_id()}) as u on d.id=u.driver_id"
  query += " where image is not null "
  print(f"Current user: {current_user.get_id()}")
  if args["name"]:
    query += " and d.name like %(name)s"
    args["name"] = "%" + args["name"] + "%"
  if args["team"]:
    query += " and s.teams like %(team)s"
    args["team"] = "%" + args["team"] + "%"
  if args["country"]:
    query += " and country = %(country)s"
  if args["favs"] == "fav":
    query += " and f.fcount > 0"
  elif args["favs"] == "nofav":
    query += " and f.fcount is null"
  if args["column"] and args["order"] and args["column"] in sortoptions and args["order"] in ["asc", "desc"]:
    if args["column"] == "favorites":
      args["column"] = "favcount"
    sorting = args["column"]
    orderby = args["order"]
    query += f" ORDER BY {sorting} {orderby}"
  try:
    if limit:
      if int(limit) <= 100 and int(limit) > 0:
          query += f" LIMIT {limit}"
      else:
          flash("Limit provided is out of bounds", "danger")
          query += " LIMIT 10"
    else:
      query += " LIMIT 10"
  # TODO search-8 provide a proper error message if limit isn't a number or if it's out of bounds
  except Exception as e:
      flash("Limit provided is not valid.", "danger")
      query += " LIMIT 10"
      print(str(e))

  try:
    result = DB.selectAll(query, args)
    #print(f"result {result.rows}")
    if result.status:
        drivers = result.rows
        print(f"rows {drivers}")
  except Exception as e:
    flash("Retrieving the driver records failed.", "danger")
    print(str(e))
  
  sortoptions = [(d, d) for d in sortoptions]
  return render_template("list_drivers.html", drivers=drivers, sortoptions=sortoptions)

# sr2484 | Apr 22
@f1.route("/driver-create", methods=["GET", "POST"])
@login_required
def create_drivers():
  drivers=[]
  remote = None
  user_id = current_user.get_id()
  drivers = request.args.get("drivers", [])
  print(drivers)
  form1 = SearchForm()
  form2 = CreateForm()
  if request.method == "GET" and len(drivers) == 0:
    print("GET")
    drivername = request.args.get("drivername", "")
    remote = request.args.get("remote","")
    print(f"Remote value: {remote}")
    if remote == "remote":
      drivers = api_get_driver(drivername)
    else:
      drivers = search_drivers(drivername)
    print(drivers)
  elif request.method == "POST":
    print("POST")
    has_error = False
    drivername = request.form.get("drivername", None)
    image = request.form.get("image", None)
    birthdate = request.form.get("birthdate", None)
    birthplace = request.form.get("country", None)
    podium = request.form.get("podiums", None)
    champion = request.form.get("championships", None)
    print(drivername, image, birthdate, podium, champion, birthplace)
    #if form2.validate():
    # Validate driver name provided. Uncomment before line when adding validation to the driver_forms.py
    if not drivername:
      flash("Driver Name is missing", "danger")
      has_error = True
    else:
      try:
        result = DB.selectOne(f"SELECT count(*) as dcount FROM IS601_f1_drivers where name = '{drivername}'")
        print(result)
        if result.status:
          if result.row["dcount"] != 0:
            flash("Provided driver records already exists. Only non-existing drivers can be added", "danger")
            has_error = True
      except Exception as e:
        print(str(e))
        flash("Cannot verify the driver name with existing records. Please contact administrator to resolve the issue")
    # Validate image provided
    valid_image_formats = [".png", ".jpeg", ".jpg", ".gif"]
    if not image:
      flash("Driver image is required to save driver", "danger")
      has_error = True
    else:
      count = len(valid_image_formats)
      for type in valid_image_formats:
        if type == image[-4:] or type == image[-5:]:
          count -= 1
      if count == len(valid_image_formats):
        has_error = True
        flash("Image is not in an acceptable format. Provide images of format PNG, JPEG or GIF", "danger")
      else:
        r = re.fullmatch("^https://.*", image)
        if not r:
          has_error = True
          flash("Image is not in the correct format. Image should be a web url", "danger")
    id = get_config_id()
    if id == 0:
      has_error = True
    if podium:
      if "." in podium:
        has_error = True
        flash("Podium should be a number and should not have decimal values", "danger")
    if champion:
      if "." in champion:
        flash("Championships should be a number and should not have decimal values", "danger")
        has_error = True
    if birthdate:
      today = datetime.today()
      bdate = datetime.strptime(birthdate, '%Y-%m-%d').date()
      diff = today.date() - bdate
      if diff.days/365 < 18:
        has_error = True
        flash("Invalid date, Age of the driver is less than 18 which is incorrect. Please provide correct birthdate", "danger")

    if not has_error:
      try:
        result = DB.insertOne("""
        INSERT INTO IS601_f1_drivers 
        (id, name, birthdate, country, podiums, championships, image, response) 
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s)
        """, id, drivername, birthdate, birthplace, podium, champion, image, f"Created by user {user_id}")
        # Update with user name above
        print(result)
        if result.status:
            flash("Added Driver", "success")
            dri={}
            dri["url"] = image
            dri["name"] = drivername
            drivers.append(dri)
            id += 1
            update_config_id(id)
      except Exception as e:
        has_error = True
        flash("Error adding the driver, name of the driver might already exist", "danger")

  return render_template("create_drivers.html", form1=form1, form2=form2, drivers=drivers, remote=remote)


# sr2484 | Apr 24
@f1.route("/driver-view", methods=["GET"])
@login_required
def view_driver():
  driver = []
  stats = []
  isfav=0
  id = request.args.get("id")
  args = {**request.args}
  query1 = f"Select id, name, country, birthdate, podiums, championships, image from IS601_f1_drivers where id = {id}"
  query2 = f"Select seasons, teams, logo from IS601_f1_driver_stats where driver_id = {id} order by seasons desc"
  query3 = f"Select count(*) as isfav from IS601_f1_userfavs where driver_id={id} and user_id={current_user.get_id()}"
  try:
    result = DB.selectOne(query1)
    if result.status and result.row:
      driver = result.row
      country_name = pycountry.countries.get(alpha_2=driver["country"])
      print(country_name)
      driver["country"] = country_name.name
      today = datetime.today()
      bdate = driver["birthdate"]
      diff = today.date() - bdate
      driver["birthdate"] = diff.days//365
      result1 = DB.selectAll(query2)
      if result1.status:
        stats = result1.rows
      result1 = DB.selectOne(query3)
      print(result1)
      if result1.status:
        isfav = result1.row["isfav"]
    else:
      flash("No data found.", "danger")
      del args["id"]
      return redirect(url_for("f1.list_drivers", **args))
  except Exception as e:
    print(f"Error {str(e)}")
    flash("Unable to reach server. Please contact administrator.", "danger")
    del args["id"]
    return redirect(url_for("f1.list_drivers", **args))
  return render_template("view_driver.html", driver=driver, stats=stats, isfav=isfav)


# sr2484 | Apr 23
@f1.route("/driver-edit", methods=["GET", "POST"])
@login_required
def edit_driver():
  form = EditForm()
  id = request.args.get("id", "0")
  rargs = {**request.args}
  if request.method == "POST":
    has_error = False
    args={}
    args["id"] = id
    args["drivername"] = request.form.get("drivername", None)
    args["image"] = request.form.get("image", None)
    args["birthdate"] = request.form.get("birthdate", None)
    args["birthplace"] = request.form.get("country", None)
    args["podiums"] = request.form.get("podiums", "-1")
    args["champion"] = request.form.get("championships", "-1")
    if not args["drivername"]:
      flash("Driver Name is missing", "danger")
      has_error = True
    else:
      try:
        result = DB.selectOne("SELECT id FROM IS601_f1_drivers where name = %s", args["drivername"])
        print(result)
        if result.status:
          dbid = result.row["id"]
          id = int(id)
          print(f"db id: {dbid} {type(dbid)}, args id: {id} {type(id)} ")
          if dbid != id:
            flash("Provided driver name already exists.", "danger")
            has_error = True
      except Exception as e:
        print(str(e))
    # Validate image provided
    valid_image_formats = [".png", ".jpeg", ".jpg", ".gif"]
    if not args["image"]:
      flash("Driver image is required to save driver", "danger")
      has_error = True
    else:
      count = len(valid_image_formats)
      for format in valid_image_formats:
        if format == args["image"][-4:] or format == args["image"][-5:]:
          count -= 1
      if count == len(valid_image_formats):
        has_error = True
        flash("Image is not in an acceptable format. Provide images of format PNG, JPEG or GIF", "danger")
      else:
        r = re.fullmatch("^https://.*", args["image"])
        if not r:
          has_error = True
          flash("Image is not in the correct format. Image should be a web url", "danger")
    if args["podiums"]:
      if "." in args["podiums"] or int(args["podiums"]) < 0:
        has_error = True
        flash("Podium should be a number and should not have decimal values or negative values", "danger")
    if args["champion"]:
      if "." in args["champion"] or int(args["champion"]) < 0:
        flash("Championships should be a number and should not have decimal values", "danger")
        has_error = True
    if args["birthdate"]:
      today = datetime.today()
      bdate = datetime.strptime(args["birthdate"], '%Y-%m-%d').date()
      diff = today.date() - bdate
      if diff.days/365 < 18:
        has_error = True
        flash("Invalid date, Age of the driver is less than 18 which is incorrect. Please provide correct birthdate", "danger")
    if not has_error:
      try:
        result = DB.update("""Update IS601_f1_drivers
        set 
        name = %(drivername)s, country = %(birthplace)s, birthdate = %(birthdate)s, podiums = %(podiums)s,
        championships = %(champion)s, image = %(image)s
        where id = %(id)s
        """, args)
        if result.status:
          flash("Driver data updated successfully", "success")
        else:
          flash("Could not update the driver record. If valid data provided please contact administrator", "danger")
          print(f"Error: {str(result.status)}")
      except Exception as e:
        print(f"Error: {str(e)}")
        flash("Please provide valid data to update", "danger")
  query = f"Select id, name, country, birthdate, podiums, championships, image from IS601_f1_drivers where id = {id}"
  country=""
  try:
    result = DB.selectOne(query)
    if result.status and result.row:
      form.birthdate.data = result.row["birthdate"]
      print(form.birthdate.data)
      form.podiums.data = result.row["podiums"]
      form.drivername.data = result.row["name"]
      form.championships.data = result.row["championships"]
      form.image.data = result.row["image"]
      country = result.row["country"]
    else:
      flash("No data found for the selected id", "danger")
      del rargs["id"]
      return redirect(url_for("f1.list_drivers", **rargs))
  except Exception as e:
    print(f"Error: {str(e)}")
    flash("Unable to reach server. Please contact administrator.", "danger")
  return render_template("edit_drivers.html", form=form, id=id, country=country)

# sr2484 | Apr 24
@f1.route("/driver-delete", methods=["GET"])
@login_required
def delete_driver():
  id = request.args.get("id")
  if not id:
      flash("Id must be set", "danger")
  
  args = {**request.args}
  print("id provided")
  if id:
    print("Valid id")
    try:
      result = DB.delete("DELETE FROM IS601_f1_driver_stats WHERE driver_id = %s", id) 
      if result.status:
        result = DB.delete("DELETE FROM IS601_f1_userfavs where driver_id = %s", id)
        if result.status:
          result = DB.delete("DELETE FROM IS601_f1_drivers where id = %s", id)
          if result.status:
            flash("Deleted record", "success")
          else:
            flash("Driver record not deleted.", "danger")
        else:
          flash("Driver record not deleted.", "danger")
      else:
        flash("Driver record not deleted.","danger")
    except Exception as e:
      flash("Driver record not deleted, Provide valid driver id", "danger")
      print(str(e))
  
  del args["id"]
  return redirect(url_for("f1.list_drivers", **args))

# sr2484 | Apr 24
def api_get_driver(name):
  print(name)
  api_val = get_api()
  api_drivers = []
  permin = 0
  perday = 0
  db_permin = permin
  db_perday = perday
  modified = datetime.now()
  today = datetime.now()
  try:
    result = DB.selectOne("SELECT permin_limit, perday_limit, modified FROM IS601_f1_config where id = 1")
    if result.status:
      permin = result.row["permin_limit"]
      perday = result.row["perday_limit"]
      db_permin = permin
      db_perday = perday
      modified = result.row["modified"]
      print(modified)
      diff = today - modified
      print(str(diff))
      if diff.days >= 1:
        perday = 100
      if diff.seconds//60 > 1:
        permin = 10
  except Exception as e:
    flash(f"Unable to retrieve configuration information", "danger")
  
  if perday > 0 and permin > 0:
    print("Get data from url")
    querystring = {"search":name}
    print(querystring)
    response = requests.request("GET", api_val["driver_url"], headers=api_val["headers"], params=querystring)
    if response.status_code == 200:
      jsonresponse = json.loads(response.text)
      returned = jsonresponse["results"]
      print(f"Results returned {returned}")
      permin -= returned
      perday -= returned
      if permin < 0:
        flash(f"Unable to retrieve {abs(permin)} records, as per minute search limit has reached", "warning")
        permin = 0
      if perday < 0:
        flash(f"Unable to retrieve {abs(perday)} records, as per day search limit has reached", "warning")
        perday = 0
      i = 0
      for item in jsonresponse["response"]:
        print(item)
        dri = {}
        did = item["id"]
        dri["url"] = item["image"]
        dri["name"] = item["name"]
        dri["id"] = item["id"]
        itemlist = [item]
        api_drivers.append(dri)
        try:
          print(itemlist)
          result = DB.insertOne("Insert into IS601_f1_drivers (id, name, response) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE response = %s ",
                    dri["id"], str(did)+"NA", json.dumps(itemlist), json.dumps(itemlist))
          print(result)
          if result.status:
            print("Driver successfully added","success")
          else:
            print("Unable to add driver to the database")
        except Exception as e:
          print(f"Error: {str(e)}")
    else:
      print(f"Error: {response}")
      print(response.text)
    
    print("Drivers retrieved from API")
    print(api_drivers)
  
  if permin == 0:
    flash("Maximum search per minute is 10 drivers. Limit reached. Please do remote search after a minute", "warning")
  if perday == 0:
    flash("Maximum search per day is 100 drivers. Limit reached. Can only remote search tomorrow.", "danger")

  if db_perday != perday or db_permin != permin:
    try:
      result = DB.update(f"UPDATE IS601_f1_config SET perday_limit = {perday}, permin_limit = {permin} where id = 1")
      if result.status:
        flash(f"Search remaining: Per Minute - {permin}, Per Day - {perday} ", "success")
    except Exception as e:
      flash("Unable to update the config information", "danger")
  
  return api_drivers

@f1.route("/add-fav", methods=["GET","POST"])
@login_required 
def fav():
  args = {**request.args}
  user = current_user.get_id()
  driver = request.args.get("did")
  print(user)
  print(driver)
  try:
    result = DB.insertOne("Insert into IS601_f1_userfavs (user_id, driver_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE user_id = user_id, driver_id = driver_id",
                          user, driver)
    if not result.status:
      flash("Unable to add favorite","danger")
  except Exception as e:
    print(str(e))
  del args["did"]
  return redirect(url_for("f1.view_driver", **args))


@f1.route("/rem-fav", methods=["GET","POST"])
@login_required 
def rem_fav():
  args = {**request.args}
  user = current_user.get_id()
  driver = request.args.get("did")
  try:
    result = DB.delete("Delete from IS601_f1_userfavs where user_id = %s and driver_id = %s",
                          user, driver)
    if not result.status:
      flash("Unable to remove favorite","danger")
    else:
      flash("Removed favorite","success")
  except Exception as e:
    print(str(e))
  del args["did"]
  return redirect(url_for("f1.view_driver", **args))

