from django import template

register = template.Library()


@register.filter
def add_class(bound_field, css_classes):
    return bound_field.as_widget(attrs={"class": css_classes})


