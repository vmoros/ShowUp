from .forms import CustomUserChangeForm, SquadForm, CustomUserForm
from .models import Concert, CustomUser, Genre, Request, Squad, Swipe
from allauth.account.admin import EmailAddress
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, reverse
from .filters import ConcertFilter


def home(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            # My squad.
            squad = request.user.squad

            # Get the eid.
            eid = request.POST.get("eid")

            # Move event from "Going" to "Interested".
            if "interested" in request.POST:
                squad.going.remove(eid)
                squad.interested.add(eid)

            # Move event from "Interested" to "Going".
            if "going" in request.POST:
                squad.interested.remove(eid)
                squad.going.add(eid)

            # Remove event from "Interested".
            if "not_interested" in request.POST:
                squad.interested.remove(eid)

            # Remove event from "Going".
            if "not_going" in request.POST:
                squad.going.remove(eid)

    return render(request, "home.html")


@login_required
def events(request):
    # My squad.
    squad = request.user.squad

    filter = ConcertFilter(
        request.GET, queryset=Concert.objects.all().order_by("datetime")
    )
    context = {
        "filter": filter,
        "interested_list": squad.interested.values_list("id", flat=True),
        "going_list": squad.going.values_list("id", flat=True),
        "unique_genres": [g.genre for g in Genre.objects.all()],
        "unique_venues": set([c.venue_name for c in Concert.objects.all()]),
        "unique_performers": set([c.performer_names for c in Concert.objects.all()]),
        "boroughs": Concert.BOROUGH_CHOICES,
    }

    # User clicked "Interested" button.
    if "interested" in request.POST:
        insert_to_list_exclusively(
            request.POST.get("interested"), squad.interested, squad.going
        )

    # User clicked "Going" button.
    if "going" in request.POST:
        insert_to_list_exclusively(
            request.POST.get("going"), squad.going, squad.interested
        )

    return render(request, "events.html", context=context)


def insert_to_list_exclusively(event_id, add_list, remove_list):
    if add_list.filter(id=event_id).count() > 0:
        add_list.remove(event_id)
    else:
        add_list.add(event_id)
        if remove_list.filter(id=event_id).count() > 0:
            remove_list.remove(event_id)


@login_required
def user(request, id):
    # See if this user exists.
    try:
        user = CustomUser.objects.get(id=id)
    except CustomUser.DoesNotExist:
        raise PermissionDenied

    # Ensure this user verified their email address.
    if not EmailAddress.objects.get(email=user.email).verified:
        raise PermissionDenied

    return render(request, "user.html", context={"requested_user": user})


@login_required
def edit_profile(request, id):
    if request.user.id == id:
        # above, on the left is the user's id, on the right is the id in the URL
        form = CustomUserChangeForm(request.POST or None, instance=request.user)
        if request.method == "POST" and form.is_valid():
            form.save()
            return redirect(reverse("user", kwargs={"id": id}))
        return render(request, "edit_profile.html", {"form": form})
    else:
        raise PermissionDenied


@login_required
def squad(request, id):
    try:
        squad = Squad.objects.get(id=id)
        users = CustomUser.objects.filter(squad=squad)
    except Squad.DoesNotExist:
        raise PermissionDenied

    return render(request, "squad.html", context={"users": users})


@login_required
def edit_squad(request, sid):
    # You can only edit your own squad.
    if sid == request.user.squad.id:
        # Get my squad.
        my_squad = request.user.squad
        squad_size = CustomUser.objects.filter(squad=my_squad).count()

        form = SquadForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            if "add" in request.POST:
                try:
                    # Get their squad.
                    their_squad = CustomUser.objects.get(
                        email=request.POST["email"]
                    ).squad
                except CustomUser.DoesNotExist:
                    msg = "{} is not registered with ShowUp.".format(
                        request.POST["email"]
                    )
                    return render(
                        request,
                        "edit_squad.html",
                        {"form": form, "msg": msg, "squad_size": squad_size},
                    )

                # We are already in the same squad.
                if my_squad.id == their_squad.id:
                    msg = "{} is already in your squad!".format(request.POST["email"])
                    return render(
                        request,
                        "edit_squad.html",
                        {"form": form, "msg": msg, "squad_size": squad_size},
                    )

                # Check to see if our squad sent a request to their squad.
                r = Request.objects.filter(requester=my_squad, requestee=their_squad)
                if r.exists():
                    msg = (
                        "A squad request has already been sent to {}. Please "
                        "wait for them to accept it.".format(request.POST["email"])
                    )
                    return render(
                        request,
                        "edit_squad.html",
                        {"form": form, "msg": msg, "squad_size": squad_size},
                    )

                # Check to see if their squad sent a request to our squad.
                r = Request.objects.filter(requester=their_squad, requestee=my_squad)
                if r.exists():
                    msg = (
                        "You already have a pending squad request from {}. "
                        "Head over to Requests to approve it.".format(
                            request.POST["email"]
                        )
                    )
                    return render(
                        request,
                        "edit_squad.html",
                        {"form": form, "msg": msg, "squad_size": squad_size},
                    )
                else:
                    # Create a request.
                    Request.objects.create(requester=my_squad, requestee=their_squad)

                    msg = (
                        "A request has been sent to {}. If they accept, your "
                        "squads will merge.".format(request.POST["email"])
                    )
                    return render(
                        request,
                        "edit_squad.html",
                        {"form": form, "msg": msg, "squad_size": squad_size},
                    )

            elif "leave" in request.POST:
                # You can only leave a squad if you're not the only one in it.
                if squad_size > 1:
                    me = CustomUser.objects.get(id=request.user.id)
                    me.squad = Squad.objects.create()
                    me.save()
                    return redirect(reverse("squad", kwargs={"id": me.squad.id}))
                else:
                    raise PermissionDenied

            else:
                raise PermissionDenied

        return render(
            request,
            "edit_squad.html",
            {"form": form, "msg": "", "squad_size": squad_size},
        )

    else:
        raise PermissionDenied


@login_required
def requests(request):
    if request.method == "POST":
        # Get my squad and their squad.
        my_squad = request.user.squad
        their_squad = Squad.objects.get(id=request.POST["their_sid"])

        if "accept" in request.POST:
            # Get the request.
            r = Request.objects.get(requester=their_squad, requestee=my_squad)

            # Join the squad that has a smaller id.
            if their_squad.id < my_squad.id:
                my_squad, their_squad = their_squad, my_squad

            # Get their members.
            their_members = CustomUser.objects.filter(squad=their_squad)

            # Merge squads.
            for member in their_members:
                member.squad = my_squad
                member.save()

            # Add their interested events.
            for event in their_squad.interested.all():
                # If event is in interested then leave it in interested.
                # If event is in going then leave it in going.
                if (
                    event not in my_squad.interested.all()
                    and event not in my_squad.going.all()
                ):
                    my_squad.interested.add(event)

            # Add their going events.
            for event in their_squad.going.all():
                # If event is in interested then put it in going.
                if event in my_squad.interested.all():
                    my_squad.interested.remove(event)
                    my_squad.going.add(event)
                # If event is not in going then put it in going.
                if event not in my_squad.going.all():
                    my_squad.going.add(event)

            # Delete their old squad.
            Squad.objects.get(id=their_squad.id).delete()

            # Delete the request.
            r.delete()
        elif "deny" in request.POST:
            # Get the request.
            r = Request.objects.filter(requester=their_squad, requestee=my_squad)

            # Delete the request.
            r.delete()
        else:
            raise PermissionDenied

    # Get all the squads that requested to join this squad.
    squads = Request.objects.filter(requestee=request.user.squad)
    squads = [x.requester for x in squads]

    if squads:
        # Get all the users of all the squads that requested to join this squad.
        users = []
        for squad in squads:
            users += CustomUser.objects.filter(squad=squad)
    else:
        users = None

    return render(request, "requests.html", {"squads": squads, "users": users})


def get_stack(request, eid):
    # My sid.
    sid = request.user.squad.id

    # Get the squads interested in or going to the event.
    squads = (
        Squad.objects.filter(interested__id=eid) | Squad.objects.filter(going__id=eid)
    ).distinct()

    # These are the squads that swiped left on my squad.
    swiped_left = [
        x.swiper.id
        for x in Swipe.objects.filter(swipee__id=sid, event__id=eid, direction=False)
    ]

    # These are the squads that my squad swiped on.
    swiped = [x.swipee.id for x in Swipe.objects.filter(swiper__id=sid, event__id=eid)]

    """
    Exclude the following squads:
    - The squads that swiped left on my squad.
    - The squads that my squad swiped on.
    - My squad.
    """
    squads = [
        s
        for s in squads
        if s.id not in swiped_left and s.id not in swiped and s.id != sid
    ]

    return squads


@login_required
def event_stack(request, eid):
    if request.method == "POST":
        # Create a Swipe object.
        my_sid = request.user.squad.id
        their_sid = request.POST["their_sid"]
        direction = True if request.POST["match"] == "True" else False

        my_swipe = Swipe.objects.create(
            swiper=Squad(id=my_sid),
            swipee=Squad(id=their_sid),
            event=Concert(id=eid),
            direction=direction,
        )

        try:
            # Check to see if their squad swiped on our squad.
            their_swipe = Swipe.objects.get(
                swiper__id=their_sid, swipee__id=my_sid, event__id=eid
            )
            if my_swipe.direction and their_swipe.direction:
                match = Squad.objects.get(id=their_sid)
            else:
                match = None
        except Swipe.DoesNotExist:
            match = None
    else:
        match = None

    # Get event details.
    event = Concert.objects.get(id=eid)

    # Get squads and users.
    squads = get_stack(request, eid)
    if squads:
        # Get all the users of all the squads that are in the stack.
        users = []
        for squad in squads:
            users += CustomUser.objects.filter(squad=squad)
    else:
        users = None

    return render(
        request,
        "match.html",
        {"event": event, "squads": squads, "users": users, "match": match},
    )


@login_required
def matches(request):
    # My sid.
    sid = request.user.squad.id

    # The squads that my squad swiped right on.
    i_swiped_right = [x for x in Swipe.objects.filter(swiper__id=sid, direction=True)]

    # The squads that swiped right on my squad.
    they_swiped_right = [
        x.swiper for x in Swipe.objects.filter(swipee__id=sid, direction=True)
    ]

    # The intersection of the above two.
    uniq_events = set()
    uniq_sid = set()
    users = []
    matches = [x for x in i_swiped_right if x.swipee in they_swiped_right]
    matches.sort(key=lambda x: x.event.id)
    for match in matches:
        uniq_events.add(match.event)
        uniq_sid.add(match.swipee)

    for id in uniq_sid:
        users += CustomUser.objects.filter(squad=id)

    return render(
        request,
        "matches.html",
        {"matches": matches, "events": uniq_events, "users": users},
    )


@login_required
def settings(request):
    msg = ""
    if request.POST:
        form = CustomUserForm(request.POST or None, instance=request.user)
        if form.is_valid():
            form.save(request)
            msg = "Settings changed successfully!"
    return render(request, "settings.html", {"user": request.user, "message": msg})


@login_required
def messages(request, squad1, squad2):
    # My sid.
    sid = request.user.squad.id

    # The squads that my squad swiped right on.
    i_swiped_right = [x for x in Swipe.objects.filter(swiper__id=sid, direction=True)]

    # The squads that swiped right on my squad.
    they_swiped_right = [
        x.swiper for x in Swipe.objects.filter(swipee__id=sid, direction=True)
    ]

    # The intersection of the above two.
    matches = [x.swipee.id for x in i_swiped_right if x.swipee in they_swiped_right]

    if request.user.squad.id != squad1:
        # If you do not belong to squad1, you do not have permission to view.
        raise PermissionDenied
    elif squad2 not in matches:
        # If squad1 did not match with squad2, they cannot chat.
        raise PermissionDenied
    else:
        # Have squad1 always be less than squad2.
        if squad1 > squad2:
            squad1, squad2 = squad2, squad1

        base_url = "https://showup-nyc-messaging.herokuapp.com/"
        return render(
            request, "messages.html", {"iframe_url": f"{base_url}{squad1}-{squad2}"}
        )
