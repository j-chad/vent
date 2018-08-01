# coding=utf-8
from typing import List

import flask
from flask_login import current_user, login_required

from event_app.models import MessageTypes
from .. import forms, models
from ..extensions import db

events = flask.Blueprint('events', __name__)


@events.route('/discover')
@login_required
def discover() -> flask.Response:
    if current_user.location_enabled:
        events_ = models.Event.query.filter(
                models.Event.distance_from(current_user.latitude, current_user.longitude)
                <= flask.current_app.config['EVENT_MAXIMUM_DISTANCE'],
                models.Event.private == False
        ).order_by(
                models.Event.distance_from(current_user.latitude, current_user.longitude),
                models.Event.start
        ).all()
        if len(events_) == 0:
            events_ = None
    else:
        events_ = None
    return flask.render_template("events/discover.jinja",
                                 events=events_,
                                 loc_enabled=current_user.location_enabled)


@events.route('/event/create', methods=("GET", "POST"))
@login_required
def create_event() -> flask.Response:
    form = forms.CreateEventForm()
    if form.validate_on_submit():
        new_event = models.Event(owner=current_user,
                                 name=form.name.data,
                                 description=form.description.data,
                                 private=form.private.data)
        db.session.add(new_event)
        db.session.commit()
        return flask.redirect("/event/{}".format(new_event.url_id))
    return flask.render_template("events/create_event_minimal.jinja", form=form)


@events.route('/event/<token>')
@login_required
def view_event(token):
    event: models.Event = models.Event.fetch_from_url_token(token)
    if event is None:
        flask.abort(404)

    subscribed: bool = models.Subscription.query.get((current_user.email, event.id)) is not None
    owner: bool = event in current_user.events
    messages: List[models.EventMessage] = models.EventMessage.query.filter_by(event=event).order_by(
            models.EventMessage.timestamp).all()
    questions: List[models.Question] = models.Question.query.filter_by(event=event).order_by(models.Question.timestamp)

    return flask.render_template("events/event_detail.jinja",
                                 event=event,
                                 subscribed=subscribed,
                                 owner=owner,
                                 user=current_user,
                                 messages=messages,
                                 questions=questions,
                                 message_types=MessageTypes)
