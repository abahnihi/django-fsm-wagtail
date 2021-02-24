"""
View classes
"""
from django.http.response import Http404
from django.utils.translation import gettext as _
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.encoding import force_text

from wagtail.contrib.modeladmin.views import InstanceSpecificView, DeleteView

# Create your views here.


class FsmConfirmationView(InstanceSpecificView):
    """
    The View class of the confirmation after click on an action bytton
    """

    page_title = _("Confirmation")

    def get_template_names(self):
        return self.model_admin.fsm_confirm_template_name

    def get_meta_title(self):
        """
        used in the template
        """
        return _("Confirm action of %s") % self.verbose_name

    def confirmation_message(self):
        """
        used in the template
        """
        return (
            _("Are you sure you want to apply the action to this %s?")
            % self.verbose_name
        )

    def fsm_transition_url(self):
        """
        used in the template
        """
        return self.url_helper.get_action_url("fsm_transition", self.pk_quoted)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        transition = self.request.GET.get("transition")

        ctx["transition_name"] = transition
        (
            ctx["transition_label"],
            fsm_field_name,
        ) = self.button_helper.get_transition_label_by_name(
            obj=self.instance, request=self.request, transition_name=transition
        )

        return ctx

    def get(self, request, *args, **kwargs):
        transition = self.request.GET.get("transition", None)
        if not transition:
            raise Http404
        valid_transition = self.button_helper.is_transition_available(
            obj=self.instance, transition=transition, request=self.request
        )
        if not valid_transition:
            raise Http404
        return super().get(request, *args, **kwargs)

    def _do_transition(self, transition, request, obj, fsm_field_name):
        original_state = self.button_helper.display_fsm_field(obj, fsm_field_name)
        msg_dict = {
            "obj": force_text(obj),
            "transition": transition,
            "original_state": original_state,
        }
        # Ensure the requested transition is available
        available = self.button_helper.is_transition_available(obj, transition, request)
        trans_func = getattr(obj, transition, None)
        if available and trans_func:
            # Run the transition
            try:
                # Attempt to pass in the request and by argument if using django-fsm-log
                trans_func(request=request, by=request.user)
            except TypeError:
                try:
                    # Attempt to pass in the by argument if using django-fsm-log
                    trans_func(by=request.user)
                except TypeError:
                    # If the function does not have a by attribute, just call with no arguments
                    trans_func()
            new_state = self.button_helper.display_fsm_field(obj, fsm_field_name)

            msg_dict.update({"new_state": new_state, "status": messages.SUCCESS})
            obj.save(update_fields=[fsm_field_name])
        else:
            msg_dict.update({"status": messages.ERROR})

        # Attach the results of our transition attempt
        setattr(obj, "_fsmtransition_results", msg_dict)

    def post(self, request, *args, **kwargs):
        """Post handler"""
        transition = self.request.GET.get("transition", None)
        if not transition:
            raise Http404
        valid_transition = self.button_helper.is_transition_available(
            obj=self.instance, transition=transition, request=self.request
        )
        if not valid_transition:
            raise Http404

        target_label, fsm_field_name = self.button_helper.get_transition_label_by_name(
            obj=self.instance, request=self.request, transition_name=transition
        )

        self._do_transition(
            transition=transition,
            request=self.request,
            obj=self.instance,
            fsm_field_name=fsm_field_name,
        )

        new_state = self.button_helper.display_fsm_field(
            obj=self.instance, fsm_field_name=fsm_field_name
        )
        msg = _("%(model_name)s '%(instance)s' is %(new_state)s") % {
            "model_name": self.verbose_name,
            "instance": self.instance,
            "new_state": new_state,
        }
        messages.success(request, msg)

        return redirect(self.index_url)
