""" Admin Module"""
from django.conf import settings
from django.urls import re_path
from django.contrib.admin.utils import quote
from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import ModelAdmin
from wagtail.contrib.modeladmin.helpers import ButtonHelper, AdminURLHelper

from .views import FsmConfirmationView


# Register your models here.


class FsmButtonHelper(ButtonHelper):
    """
    Here we add the transition buttons
    """

    # Define classes for our button, here we can set an icon for example
    view_button_classnames = ["button-small", "icon", "icon-site"]

    def _get_fsm_field_list(self):
        """
        Ensure backward compatibility by converting a single fsm field to
        a list.  While we are guaranteeing compatibility we should use
        this method to retrieve the fsm field rather than directly
        accessing the property.
        """
        if not isinstance(self.view.model_admin.fsm_field, (list, tuple,)):
            return [self.view.model_admin.fsm_field]

        return self.view.model_admin.fsm_field

    def _filter_admin_transitions(self, transitions_generator):
        """
        Filter the given list of transitions, if their transition methods are declared as admin
        transitions. To allow a transition inside fsm_admin, add the parameter
        `admin=True` to the transition decorator, for example:
        ```
        @transition(field='state', source=['startstate'], target='finalstate', custom=dict(admin=True))
        def do_something(self):
            ...
        ```
        If the configuration setting `FSM_ADMIN_FORCE_PERMIT = True` then only transitions with
        `custom=dict(admin=True)` are allowed. Otherwise, if `FSM_ADMIN_FORCE_PERMIT = False` or
        unset only those with `custom=dict(admin=False)`
        """
        for transition in transitions_generator:
            if transition.custom.get(
                "admin", self.view.model_admin.default_disallow_transition
            ):
                yield transition

    def is_transition_available(self, obj, transition, request):
        """
        Checks if the requested transition is available
        """
        transitions = []
        for field, field_transitions in iter(
            self.fsm_get_transitions(obj, request).items()
        ):
            transitions += [t.name for t in field_transitions]
        return transition in transitions

    def get_transition_label_by_name(self, obj, request, transition_name):
        transitions = self.fsm_get_transitions(obj=obj, request=request)
        transition_label = None
        fsm_field_name = None
        for field_name, actions in transitions.items():
            for action in actions:
                if action.name == transition_name:
                    transition_label = action.custom.get("label", action.name)
                    fsm_field_name = field_name
        return transition_label, fsm_field_name

    def fsm_get_transitions(self, obj, request):
        """
        Gets a list of transitions available to the user.
        Available state transitions are provided by django-fsm
        following the pattern get_available_FIELD_transitions

        Used in FsmButtonHelper and in templatetags fsm_wagtail_actions
        """
        user = request.user
        fsm_fields = self._get_fsm_field_list()

        transitions = {}
        for field in fsm_fields:
            transitions_func = "get_available_user_{0}_transitions".format(field)
            transitions_generator = getattr(obj, transitions_func)(user) if obj else []
            transitions[field] = self._filter_admin_transitions(transitions_generator)
        return transitions

    def fsm_field_instance(self, fsm_field_name):
        """
        Returns the actual state field instance, as opposed to
        fsm_field attribute representing just the field name.
        """
        return self.view.model_admin.model._meta.get_field(fsm_field_name)

    def display_fsm_field(self, obj, fsm_field_name):
        """
        Makes sure get_FOO_display() is used for choices-based FSM fields.
        """
        field_instance = self.fsm_field_instance(fsm_field_name)
        if field_instance and field_instance.choices:
            return getattr(obj, "get_%s_display" % fsm_field_name)()
        else:
            return getattr(obj, fsm_field_name)

    def fsm_buttons(self, pk, classnames_add=None, classnames_exclude=None):
        """ Return FSM button array of dictionaries"""
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []

        if "/inspect/" in self.request.path:  # in Inspect View, buttons are not small
            cn = "button fsm_transition"
        else:
            cn = "button fsm_transition button-small button-secondary "

        if (
            hasattr(self.view, "instance") and self.view.instance
        ):  # We are in InspectView, EditView
            obj = self.view.instance
        else:
            obj = self.view.queryset.get(pk=pk)
        transitions = self.fsm_get_transitions(obj=obj, request=self.view.request)
        buttons = []
        for field_name, actions in transitions.items():
            for action in actions:
                classname = action.custom.get("button_color", "")
                label = action.custom.get("label", action.name)
                buttons.append(
                    {
                        "url": self.url_helper.get_action_url(
                            "fsm_transition", quote(pk)
                        )
                        + "?transition=%s" % action.name,
                        "state": self.display_fsm_field(obj, fsm_field_name=field_name),
                        "label": label,
                        "classname": "%s %s" % (cn, classname),
                        "title": _("%s this %s") % (label, self.verbose_name),
                    }
                )
        return buttons

    def get_buttons_for_obj(
        self, obj, exclude=None, classnames_add=None, classnames_exclude=None
    ):
        """
        This function is used to gather all available buttons.
        We append our custom button to the btns list.
        """
        btns = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude
        )

        if "fsm_button" not in (exclude or []):
            for button in self.fsm_buttons(obj.pk):
                btns.append(button)
        return btns


class FsmAdminURLHelper(AdminURLHelper):
    """
    For any required customization
    """


class FsmWagtailAdminMixin(ModelAdmin):
    """
    Inheret the ModelAdmin from this class
    """

    default_disallow_transition = not getattr(
        settings, "WAGTAIL_FSM_ADMIN_FORCE_PERMIT", False
    )

    button_helper_class = FsmButtonHelper
    url_helper_class = FsmAdminURLHelper
    fsm_transition_view_class = FsmConfirmationView

    fsm_confirm_template_name = "fsm_wagtail/modeladmin_confirm_action.html"

    def get_index_view_extra_css(self):
        css = super().get_index_view_extra_css()
        return css + ["fsm_wagtail/css/fsm_wagtail_admin.css"]

    def get_index_view_extra_js(self):
        js = super().get_index_view_extra_js()
        return js + ["fsm_wagtail/js/fsm_wagtail_admin.js"]

    def get_inspect_view_extra_css(self):
        css = super().get_index_view_extra_css()
        return css + ["fsm_wagtail/css/fsm_wagtail_admin.css"]

    def get_inspect_view_extra_js(self):
        js = super().get_index_view_extra_js()
        return js + ["fsm_wagtail/js/fsm_wagtail_admin.js"]

    def get_admin_urls_for_registration(self):
        urls = super().get_admin_urls_for_registration()
        url_pattern = self.url_helper.get_action_url_pattern("fsm_transition")
        view_function = self.fsm_transition_view
        url_name = self.url_helper.get_action_url_name("fsm_transition")
        urls += (re_path(url_pattern, view_function, name=url_name),)
        return urls

    def fsm_transition_view(self, request, instance_pk):
        """
        The view function of the new registered url
        """
        kwargs = {"model_admin": self, "instance_pk": instance_pk}
        view_class = self.fsm_transition_view_class
        return view_class.as_view(**kwargs)(request)
