from flask import Blueprint, redirect, request, render_template, url_for, flash, current_app
import requests
import json
import os
import re
import pycountry
from datetime import datetime
from f1.story_forms import CreateForm, EditForm
from flask_login import current_user, login_required
from roles.permissions import admin_permission
from sql.db import DB
story = Blueprint('story', __name__, url_prefix='/', template_folder="templates")

# sr2484 | May 2
@story.route("/create-story", methods=["GET", "POST"])
@login_required
def create_story():
  user_id = current_user.get_id()
  form = CreateForm()
  storedrivers = []
  try:
    result = DB.selectAll("select id, name, image from IS601_f1_drivers where image is not null and id > 0")
    if result.status:
      if len(result.rows) > 0:
        storedrivers = [(r["id"], r["name"]) for r in result.rows]
    else:
      flash("Unable to retrieve driver information. You are allowed to create stories without linking to any drivers", "warning")
  except Exception as e:
    flash("Unable to retrieve driver information. You are allowed to create stories without linking to any drivers", "warning")

  if request.method == "POST":
    print("POST")
    has_error = False
    short_desc = request.form.get("shortdesc", None)
    long_desc = request.form.get("longdesc", None)
    image = request.form.get("image", None)
    driver = request.form.getlist("drivers")
    print("Values of multi select driver")
    print(driver)
    if not short_desc:
      flash("Story title is missing", "danger")
      has_error = True
    else:
      try:
        result = DB.selectOne(f"SELECT count(*) as dcount FROM IS601_f1_story where short_desc = '{short_desc}'")
        print(result)
        if result.status:
          if result.row["dcount"] != 0:
            flash("Provided story title already exists. Modify the story title to add.", "danger")
            has_error = True
      except Exception as e:
        print(str(e))
        flash("Cannot verify the Story title with existing records. Please contact administrator to resolve the issue")
        has_error = True
    # Validate image provided
    valid_image_formats = [".png", ".jpeg", ".jpg", ".gif"]
    if not image:
      flash("Story image is required. Please provide the url of the image", "danger")
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
    
    if not long_desc:
      flash("Detailed story description is missing", "danger")
      has_error = True

    if not has_error:
      try:
        result = DB.insertOne("""
        INSERT INTO IS601_f1_story 
        (short_desc, long_desc, created_by, imagestr) 
        VALUES 
        (%s, %s, %s, %s)
        """, short_desc, long_desc, user_id, image)
        # Update with user name above
        print(result)
        if result.status:
          flash("Story Created...", "success")
          if len(driver) > 0:
            result=DB.selectOne(f"Select id from IS601_f1_story where short_desc='{short_desc}'")
            if result.status:
              mapping = []
              for d in driver:
                if d != 0:
                  mapping.append((d,result.row["id"]))
              if len(mapping) > 0:
                result = DB.insertMany("INSERT INTO IS601_f1_driverstory(driver_id, story_id) VALUES(%s, %s)",mapping)
                if not result.status:
                  flash(f"Unable to link {len(mapping)} drivers to story . Please contact administrator","danger")
                else:
                  flash("Story added successfully...","success")
            else:
              flash("Error while linking story to the drivers...", "danger")
      except Exception as e:
        has_error = True
        flash("Error adding the story, please contact the administrator", "danger")
    else:
      form.shortdesc.data = short_desc
      form.longdesc.data = long_desc
      form.image.data = image

  return render_template("create_story.html", form=form, drivers=storedrivers)


# sr2484 | May 2
@story.route("/list-stories", methods=["GET"])
@login_required
def list_story():
  stories = []
  args = {}
  rargs = {**request.args}
  sortoptions = ["title","Recently updated"]
  args["did"] = request.args.get("did")
  args["desc"] = request.args.get("desc")
  args["order"] = request.args.get("order")
  args["column"] = request.args.get("column")
  limit = request.args.get("limit")
  query = """Select distinct id, short_desc, imagestr, modified
            from IS601_f1_story as s 
            LEFT JOIN IS601_f1_driverstory as ds on s.id=ds.story_id
            where s.imagestr is not null """
  
  print(args["did"])
  if args["did"] != 'None' and args["did"]:
    print(args["did"])
    query += " and ds.driver_id = %(did)s"
  if args["desc"]:
    query += " and s.short_desc like %(desc)s"
    args["desc"] = "%" + args["desc"] + "%"
  print(args["column"])
  if args["column"] and args["order"] and args["column"] in sortoptions and args["order"] in ["asc", "desc"]:
    if args["column"] == "title":
      args["column"] = "short_desc"
    elif args["column"] == "Recently updated":
      args["column"] = "modified"
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
    print(query)
    print(args)
    result = DB.selectAll(query, args)
    #print(f"result {result.rows}")
    if result.status:
        stories = result.rows
        print(f"rows {stories}")
  except Exception as e:
    flash("Retrieving the driver records failed.", "danger")
    print(str(e))
  
  sortoptions = [(d, d) for d in sortoptions]
  return render_template("list_story.html", stories=stories, sortoptions=sortoptions, **rargs)


@story.route("/view-story", methods=["GET"])
@login_required
def view_story():
  story = ""
  id = request.args.get("id")
  print(id)
  args = {**request.args}
  query1 = f"Select short_desc, long_desc, imagestr from IS601_f1_story where id = {id}"
  try:
    result = DB.selectOne(query1)
    print(result.row)
    if result.status and result.row:
      story = result.row
    else:
      flash("No data found.", "danger")
      del args["id"]
      return redirect(url_for("story.list_story", **args))
  except Exception as e:
    print(f"Error {str(e)}")
    flash("Unable to reach server. Please contact administrator.", "danger")
    del args["id"]
    return redirect(url_for("story.list_story", **args))
  return render_template("view_story.html", story=story)


# sr2484 | May 2
@story.route("/edit-story", methods=["GET", "POST"])
@login_required
def edit_story():
  user_id = current_user.get_id()
  form = EditForm()
  id = request.args.get("id")
  storedrivers = []
  selected = []
  driver = []
  story={}

  if request.method == "POST":
    print("POST")
    has_error = False
    short_desc = request.form.get("shortdesc", None)
    long_desc = request.form.get("longdesc", None)
    image = request.form.get("image", None)
    driver = request.form.getlist("drivers")
    print("Values of multi select driver")
    print(driver)
    if not short_desc:
      flash("Story title is missing", "danger")
      has_error = True
    else:
      try:
        result = DB.selectOne(f"SELECT count(*) as dcount FROM IS601_f1_story where short_desc = '{short_desc}' and id != {id}")
        print(result)
        if result.status:
          if result.row["dcount"] != 0:
            flash("Provided story title already exists. Modify the story title to update.", "danger")
            has_error = True
      except Exception as e:
        print(str(e))
        flash("Cannot verify the Story title with existing records. Please contact administrator to resolve the issue")
        has_error = True
    # Validate image provided
    valid_image_formats = [".png", ".jpeg", ".jpg", ".gif"]
    if not image:
      flash("Story image is required. Please provide the url of the image", "danger")
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
    
    if not long_desc:
      flash("Detailed story description is missing", "danger")
      has_error = True

    if not has_error:
      rargs={"short_desc":short_desc, "long_desc":long_desc, "imagestr":image, "user_id":user_id, "id":id}
      try:
        result = DB.update("""
        UPDATE IS601_f1_story 
        set short_desc = %(short_desc)s, long_desc=%(long_desc)s, created_by=%(user_id)s, imagestr=%(imagestr)s 
        where id = %(id)s 
        """, rargs)
        # Update with user name above
        print(result)
        if result.status:
          flash("Story Updated...", "success")
          result=DB.selectAll(f"Select driver_id, story_id from IS601_f1_driverstory where story_id='{id}'")
          if result.status:
            dellist = []
            driver = [int(d) for d in driver]
            print(driver)
            print(result.rows)
            dbdriver = [r["driver_id"] for r in result.rows]
            print(dbdriver)
            for r in dbdriver:
              if r not in driver:
                print("does not exist")
                dellist.append(r)
            for d in driver:
              if d in dbdriver:
                print("exists driver, no addition required")
                driver.remove(d)               
            print(f"Deleting list: {dellist}")
            print(f"Adding List: {driver}") 
            mapping = []
            if len(driver) > 0:
              for d in driver:
                if d != 0:
                  mapping.append((d,id))
            if len(mapping) > 0:
              result = DB.insertMany("INSERT INTO IS601_f1_driverstory(driver_id, story_id) VALUES(%s, %s)",mapping)
              if not result.status:
                flash(f"Unable to link {len(mapping)} drivers to story . Please contact administrator","danger")
            if len(dellist) > 0:
              for d in dellist:
                result = DB.delete("Delete from IS601_f1_driverstory where driver_id=%s and story_id=%s", d, id)
                if result.status:
                  continue
                else:
                  flash(f"Unable to delete the driver {d} link to the story")
                  continue
          else:
            flash("Error while linking story to the drivers...", "danger")
      except Exception as e:
        has_error = True
        flash("Error adding the story, please contact the administrator", "danger")

  try:
    result = DB.selectOne(f"select id, short_desc, long_desc, imagestr from IS601_f1_story where imagestr is not null and id = {id}")
    if result.status:
      form.shortdesc.data = result.row["short_desc"]
      form.longdesc.data = result.row["long_desc"]
      form.image.data = result.row["imagestr"]
      result = DB.selectAll(f"Select driver_id from IS601_f1_driverstory where story_id = {id}")
      if result.status:
        for r in result.rows:
          selected.append(r["driver_id"])
      result = DB.selectAll("Select id, name from IS601_f1_drivers where image is not null and id > 0")
      if result.status:
        storedrivers = [(r["id"], r["name"]) for r in result.rows]
    else:
      flash("Unable to retrieve driver information. You are allowed to create stories without linking to any drivers", "warning")
  except Exception as e:
    print(f"Error : {str(e)}")
    flash("Unable to retrieve driver information. You are allowed to create stories without linking to any drivers", "warning")
  print(selected)
  return render_template("edit_story.html", form=form, drivers=storedrivers, selected=selected)


# sr2484 | Apr 24
@story.route("/story-delete", methods=["GET"])
@login_required
def delete_story():
  id = request.args.get("id")
  if not id:
      flash("Id must be set", "danger")
  
  args = {**request.args}
  print("id provided")
  if id:
    print("Valid id")
    try:
      result = DB.delete("DELETE FROM IS601_f1_driverstory WHERE story_id = %s", id) 
      if result.status:
        result = DB.delete("DELETE FROM IS601_f1_story where id = %s", id)
        if result.status:
          flash("Story deleted...", "success")
        else:
          flash("Story not deleted", "danger")
      else:
        flash("Story not deleted", "danger")
    except Exception as e:
      flash("Driver record not deleted, Provide valid driver id", "danger")
      print(str(e))
  
  del args["id"]
  return redirect(url_for("story.list_story", **args))