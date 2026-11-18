from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView

from .calculations import calculate_batch_ratios
from .forms import RatioCalculatorForm
from .models import RatioTemplate


class RatioCalculatorView(LoginRequiredMixin, FormView):
    """Recipe & Ratio Calculator computing container working volume, salt, and sugar grams."""

    template_name = "batches/calculator.html"
    form_class = RatioCalculatorForm

    def get_initial(self):
        initial = super().get_initial()
        template_id = self.request.GET.get("template")
        if template_id and template_id.isdigit():
            template = (
                RatioTemplate.objects.select_related("ferment_type")
                .filter(pk=int(template_id), is_active=True)
                .first()
            )
            if template:
                initial["ratio_template"] = template
                initial["salt_ratio"] = template.salt_ratio
                initial["sugar_ratio"] = template.sugar_ratio
                initial["default_duration_days"] = template.default_duration_days
        return initial

    def _build_template_payload(self):
        templates = RatioTemplate.objects.select_related("ferment_type").filter(
            is_active=True, ferment_type__is_active=True
        )
        return {
            str(tpl.pk): {
                "name": tpl.name,
                "ferment_type": tpl.ferment_type.name,
                "salt_ratio": str(tpl.salt_ratio) if tpl.salt_ratio is not None else "",
                "sugar_ratio": str(tpl.sugar_ratio) if tpl.sugar_ratio is not None else "",
                "duration": tpl.default_duration_days,
            }
            for tpl in templates
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates_data"] = self._build_template_payload()
        if "calculation" not in context:
            initial = self.get_initial()
            salt_val = initial.get("salt_ratio")
            sugar_val = initial.get("sugar_ratio")
            if salt_val is None and sugar_val is None:
                salt_val = Decimal("2.20")
            context["calculation"] = calculate_batch_ratios(
                jar_capacity_ml=initial.get("jar_capacity", Decimal("1000.00")),
                headspace_percent=initial.get("headspace_percent", Decimal("15.00")),
                produce_weight_g=initial.get("produce_weight_g", Decimal("0.00")),
                salt_ratio=salt_val,
                sugar_ratio=sugar_val,
            )
            context["selected_salt_ratio"] = salt_val
            context["selected_sugar_ratio"] = sugar_val
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        calculation = calculate_batch_ratios(
            jar_capacity_ml=data["jar_capacity"],
            headspace_percent=data["headspace_percent"],
            produce_weight_g=data.get("produce_weight_g"),
            salt_ratio=data.get("salt_ratio"),
            sugar_ratio=data.get("sugar_ratio"),
        )
        return self.render_to_response(
            self.get_context_data(
                form=form,
                calculation=calculation,
                selected_template=data.get("ratio_template"),
                selected_salt_ratio=data.get("salt_ratio"),
                selected_sugar_ratio=data.get("sugar_ratio"),
            )
        )
