# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import logging
import sys
from datetime import datetime
from logging import FileHandler, Formatter

import babel.dates
import dateutil.parser
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_migrate import Migrate
from flask_moment import Moment
from forms import ArtistForm, ShowForm, VenueForm

# ----------------------------------------------------------------------------#
# App Config
# ----------------------------------------------------------------------------#
app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")
from models import Artist, Show, Venue, db  # noqa: E0402

db.init_app(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Filters
# ----------------------------------------------------------------------------#
def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers
# ----------------------------------------------------------------------------#
@app.route("/")
def index():
    return render_template("pages/home.html")


# ----------------------------------------------------------------------------#
#  Venues
# ----------------------------------------------------------------------------#
@app.route("/venues")
def venues():
    venues = db.session.query(Venue).all()
    areas = (
        db.session.query(Venue)
        .distinct(Venue.city, Venue.state)
        .order_by(Venue.state, Venue.city)
        .all()
    )
    data = []
    for area in areas:
        data.append(
            {
                "city": area.city,
                "state": area.state,
                "venues": [
                    {
                        "id": venue.id,
                        "name": venue.name,
                        "num_upcoming_shows": len(
                            [show for show in venue.shows if show.start_time > datetime.now()]
                        ),
                    }
                    for venue in venues
                    if venue.city == area.city and venue.state == area.state
                ],
            }
        )
    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form.get("search_term", "")
    results = db.session.query(Venue).filter(Venue.name.ilike(f"%{search_term}%")).all()
    data = []
    for result in results:
        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcoming_shows": db.session.query(Show)
                .filter(Show.venue_id == result.id, Show.start_time > datetime.now())
                .count(),
            }
        )
    response = {"count": len(results), "data": data}
    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    venue = db.session.get(Venue, venue_id)
    if not venue:
        return render_template("errors/404.html")

    past_shows = []
    upcoming_shows = []
    for show in venue.shows:
        temp_show = {
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
        }
        if show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    data = vars(venue)
    data["past_shows"] = past_shows
    data["upcoming_shows"] = upcoming_shows
    data["past_shows_count"] = len(past_shows)
    data["upcoming_shows_count"] = len(upcoming_shows)

    return render_template("pages/show_venue.html", venue=data)


# ----------------------------------------------------------------------------#
#  Create Venue
# ----------------------------------------------------------------------------#
@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    form = VenueForm(request.form, meta={"csrf": False})
    if form.validate():
        try:
            venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                genres=form.genres.data,
                facebook_link=form.facebook_link.data,
                image_link=form.image_link.data,
                website=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data,
            )
            db.session.add(venue)
            db.session.commit()
        except ValueError as e:
            print(e)
            db.session.rollback()
        finally:
            db.session.close()
        # on successful db insert, flash success
        flash("Venue " + request.form["name"] + " was successfully listed!")
        return render_template("pages/home.html")
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash("Please fix the following errors: " + ", ".join(message))
        form = VenueForm()
        return render_template("forms/new_venue.html", form=form)


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    error = False
    try:
        db.session.get(Venue, venue_id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash(f"An error occurred.  Venue {venue_id} could not be deleted.")
    if not error:
        flash(f"Venue {venue_id} was successfully deleted.")
    # TODO: BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return render_template("pages/home.html")


# ----------------------------------------------------------------------------#
#  Artists
# ----------------------------------------------------------------------------#
@app.route("/artists")
def artists():
    data = db.session.query(Artist).order_by(Artist.name).all()
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form.get("search_term", "")
    results = db.session.query(Artist).filter(Artist.name.ilike(f"%{search_term}%")).all()
    data = []
    for result in results:
        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcoming_shows": db.session.query(Show)
                .filter(Show.venue_id == result.id, Show.start_time > datetime.now())
                .count(),
            }
        )
    response = {"count": len(results), "data": data}
    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    artist = db.session.get(Artist, artist_id)
    if not artist:
        return render_template("errors/404.html")

    past_shows = []
    upcoming_shows = []
    for show in artist.shows:
        temp_show = {
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "venue_image_link": show.Venue.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
        }
        if show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    data = vars(artist)
    data["past_shows"] = past_shows
    data["upcoming_shows"] = upcoming_shows
    data["past_shows_count"] = len(past_shows)
    data["upcoming_shows_count"] = len(upcoming_shows)

    return render_template("pages/show_artist.html", artist=data)


# ----------------------------------------------------------------------------#
#  Update
# ----------------------------------------------------------------------------#
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = db.session.get(Artist, artist_id)
    if artist is not None:
        form.name.data = artist.name
        form.genres.data = artist.genres
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.website_link.data = artist.website
        form.facebook_link.data = artist.facebook_link
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description
        form.image_link.data = artist.image_link
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    error = False
    artist = db.session.get(Artist, artist_id)
    try:
        artist.name = request.form["name"]
        artist.genres = request.form.getlist("genres")
        artist.city = request.form["city"]
        artist.state = request.form["state"]
        artist.phone = request.form["phone"]
        artist.website = request.form["website_link"]
        artist.facebook_link = request.form["facebook_link"]
        artist.seeking_venue = True if "seeking_venue" in request.form else False
        artist.seeking_description = request.form["seeking_description"]
        artist.image_link = request.form["image_link"]
        db.session.commit()
    except Exception:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash("An error occurred.  Artist could not be changed.")
    if not error:
        flash("Artist was successfully updated!")
    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    venue = db.session.get(Venue, venue_id)
    if venue is not None:
        form.name.data = venue.name
        form.genres.data = venue.genres
        form.address.data = venue.address
        form.city.data = venue.city
        form.state.data = venue.state
        form.phone.data = venue.phone
        form.website_link.data = venue.website
        form.facebook_link.data = venue.facebook_link
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description
        form.image_link.data = venue.image_link
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    error = False
    venue = db.session.get(Venue, venue_id)
    try:
        venue.name = request.form["name"]
        venue.genres = request.form.getlist("genres")
        venue.address = request.form["address"]
        venue.city = request.form["city"]
        venue.state = request.form["state"]
        venue.phone = request.form["phone"]
        venue.website = request.form["website_link"]
        venue.facebook_link = request.form["facebook_link"]
        venue.seeking_talent = True if "seeking_talent" in request.form else False
        venue.seeking_description = request.form["seeking_description"]
        venue.image_link = request.form["image_link"]
        db.session.commit()
    except Exception:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash("An error occurred.  Venue could not be changed.")
    if not error:
        flash("Venue was successfully updated!")
    return redirect(url_for("show_venue", venue_id=venue_id))


# ----------------------------------------------------------------------------#
#  Create Artist
# ----------------------------------------------------------------------------#
@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    form = ArtistForm(request.form, meta={"csrf": False})
    if form.validate():
        try:
            artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=form.genres.data,
                facebook_link=form.facebook_link.data,
                image_link=form.image_link.data,
                website=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
            )
            db.session.add(artist)
            db.session.commit()
        except ValueError as e:
            print(e)
            db.session.rollback()
        finally:
            db.session.close()
        # on successful db insert, flash success
        flash("Artist " + request.form["name"] + " was successfully listed!")
        return render_template("pages/home.html")
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash("Please fix the following errors: " + ", ".join(message))
        form = ArtistForm()
        return render_template("forms/new_artist.html", form=form)


# ----------------------------------------------------------------------------#
#  Shows
# ----------------------------------------------------------------------------#
@app.route("/shows")
def shows():
    shows_query = db.session.query(Show, Venue, Artist).join(Venue).join(Artist).all()
    data = []
    for show, venue, artist in shows_query:
        data.append(
            {
                "venue_id": show.venue_id,
                "venue_name": venue.name,
                "artist_id": show.artist_id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
            }
        )
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    form = ShowForm(request.form, meta={"csrf": False})
    if form.validate():
        try:
            show = Show(
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data,
                start_time=form.start_time.data,
            )
            db.session.add(show)
            db.session.commit()
        except ValueError as e:
            print(e)
            db.session.rollback()
        finally:
            db.session.close()
        # on successful db insert, flash success
        flash("Show was successfully listed!")
        return render_template("pages/home.html")
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash("Please fix the following errors: " + ", ".join(message))
        form = ShowForm()
        return render_template("forms/new_show.html", form=form)


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
