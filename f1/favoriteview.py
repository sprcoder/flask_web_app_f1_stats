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
fav = Blueprint('fav', __name__, url_prefix='/', template_folder="templates")

# sr2484 | May 3
@fav.route("/myfavorite", methods=["GET"])
@login_required
def myfav():
  user = current_user.get_id()
  favcount = 0
  drivers = []
  args = {}
  sortoptions = ["name", "country", "podiums", "championships", "favorites"]
  query = f"""Select distinct id, name, country, birthdate, podiums, championships, image, IFNULL(f.fcount, 0) as favcount, IFNULL(u.userfav, 0) as userfav
            from IS601_f1_drivers as d 
            LEFT JOIN IS601_f1_driver_stats as s on d.id=s.driver_id 
            LEFT JOIN (select driver_id, count(*) as fcount from IS601_f1_userfavs group by driver_id) as f on d.id=f.driver_id
            INNER JOIN (select driver_id, 1 as userfav from IS601_f1_userfavs where user_id={user}) as u on d.id=u.driver_id
            where image is not null """

  args["team"] = request.args.get("team")
  args["country"] = request.args.get("country")
  args["column"] = request.args.get("column")
  args["order"] = request.args.get("order")
  limit = request.args.get("limit")
  args["name"] = request.args.get("drivername")
  if args["name"]:
    query += " and d.name like %(name)s"
    args["name"] = "%" + args["name"] + "%"
  if args["team"]:
    query += " and s.teams like %(team)s"
    args["team"] = "%" + args["team"] + "%"
  if args["country"]:
    query += " and country = %(country)s"
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
      result = DB.selectOne(f"Select count(*) as favcount from IS601_f1_userfavs where user_id = {user}")
      if result.status:
        favcount = result.row["favcount"]
  except Exception as e:
    flash("Retrieving the driver records failed.", "danger")
    print(str(e))
  
  sortoptions = [(d, d) for d in sortoptions]
  return render_template("my_favorite.html", drivers=drivers, sortoptions=sortoptions, favcount=favcount)

@fav.route("/removefav", methods=["GET","POST"])
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
  except Exception as e:
    print(str(e))
  del args["did"]
  return redirect(url_for("fav.myfav", **args))


@fav.route("/remfavbyadmin", methods=["GET","POST"])
@login_required 
def rem_fav_admin():
  args = {**request.args}
  user = current_user.get_id()
  driver = request.args.get("did")
  userlist = request.args.getlist("userselected")
  print(userlist)
  if userlist:
    userlist = [int(u) for u in userlist]
  query = f"DELETE FROM IS601_f1_userfavs where driver_id = {driver} and user_id IN ("
  if userlist and len(userlist) > 0:
    for ul in userlist:
      query += f"{ul},"
    query = query[:-1]
  else:
    query += f"{user}"
  query += ")"
  try:
    result = DB.delete(query)
    if not result.status:
      flash("Unable to remove favorite","danger")
    else:
      flash("Removed the driver as favorite for the selected users", "success")
  except Exception as e:
    print(str(e))
  del args["did"]
  del args["users"]
  del args["userselected"]
  return redirect(url_for("fav.user_fav_manage", users=userlist, **args))

@fav.route("/addfavs", methods=["GET","POST"])
@login_required 
def add_fav():
  args = {**request.args}
  user = current_user.get_id()
  driver = request.args.get("did",'')
  userlist = request.args.getlist("userselected")
  print(userlist)
  if userlist:
    userlist = [int(u) for u in userlist]
  addlist = [(ul, int(driver)) for ul in userlist]
  try:
    result = DB.insertMany("Insert into IS601_f1_userfavs (user_id, driver_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE user_id = user_id, driver_id = driver_id", addlist)
    if not result.status:
      flash("Unable to add favorites","danger")
    else:
      flash("Added driver as favorites to the users", "success")
  except Exception as e:
    flash("Unable to add favorites","danger")
    print(str(e))
  del args["did"]
  del args["users"]
  del args["userselected"]
  return redirect(url_for("fav.user_fav_manage", users=userlist, **args))



@fav.route("/remove-all-fav", methods=["GET","POST"])
@login_required 
def rem_all_fav():
  user = current_user.get_id()
  print("users")
  try:
    result = DB.delete("Delete from IS601_f1_userfavs where user_id = %s", user)
    print(result)
    if not result.status:
      flash("Unable to remove favorite","danger")
    else:
      flash("Removed all favorites", "success")
  except Exception as e:
    print(str(e))
  return redirect(url_for("fav.myfav"))

@fav.route("/user-fav-manager", methods=["GET","POST"])
@admin_permission.require(http_exception=403)
def user_fav_manage():
  user = request.args.getlist("users")
  if user:
    user = [int(u) for u in user]
  print(f"Users selected : {user}")
  if not user and len(user) == 0:
    user = current_user.get_id()
    user = int(user)
    print("no user")
    print(user)
  favcount = 0
  selecteduser = []
  drivers = []
  allusers = []
  args = {}
  sortoptions = ["name", "country", "podiums", "championships", "favorites"]
  query = """Select distinct id, name, country, birthdate, podiums, championships, image, IFNULL(f.fcount, 0) as favcount, IFNULL(u.userfav, 0) as userfav
            from IS601_f1_drivers as d 
            LEFT JOIN IS601_f1_driver_stats as s on d.id=s.driver_id 
            LEFT JOIN (select driver_id, count(*) as fcount from IS601_f1_userfavs group by driver_id) as f on d.id=f.driver_id"""
  if type(user) != list:
    selecteduser = [user]
    query += f" LEFT JOIN (select driver_id, 1 as userfav from IS601_f1_userfavs where user_id={user}) as u on d.id=u.driver_id"
  elif type(user) == list and len(user) > 0:
    selecteduser = user
    query += " LEFT JOIN (select driver_id, 1 as userfav, count(*) from IS601_f1_userfavs where user_id in ("
    for ul in user:
      query += f"{ul},"
    query = query[:-1]
    query += f") group by driver_id having count(*) >= {len(user)}) as u on d.id=u.driver_id"
  query += " where image is not null "

  args["team"] = request.args.get("team")
  args["country"] = request.args.get("country")
  args["column"] = request.args.get("column")
  args["order"] = request.args.get("order")
  limit = request.args.get("limit")
  args["name"] = request.args.get("drivername")
  if args["name"]:
    query += " and d.name like %(name)s"
    args["name"] = "%" + args["name"] + "%"
  if args["team"]:
    query += " and s.teams like %(team)s"
    args["team"] = "%" + args["team"] + "%"
  if args["country"]:
    query += " and country = %(country)s"
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
  except Exception as e:
    flash("Limit provided is not valid.", "danger")
    query += " LIMIT 10"
    print(str(e))

  print(query)
  try:
    result = DB.selectAll(query, args)
    #print(f"result {result.rows}")
    if result.status:
      drivers = result.rows
      print(f"rows {drivers}")
    else:
      flash("Unable to retrieve drivers with selected features")
  except Exception as e:
    flash("Retrieving the driver records failed.", "danger")
    print(str(e))
  
  try:
    result = DB.selectAll("Select id, username from IS601_sr2484_Users where id > 0")
    if result.status:
      allusers = [(r["id"], r["username"]) for r in result.rows]
  except Exception as e:
    print(str(e))
    flash("Unable to retrieve users list","danger")
  sortoptions = [(d, d) for d in sortoptions]
  print(selecteduser)
  return render_template("admin_fav.html", drivers=drivers, sortoptions=sortoptions, favcount=favcount, allusers=allusers, selecteduser=selecteduser)

