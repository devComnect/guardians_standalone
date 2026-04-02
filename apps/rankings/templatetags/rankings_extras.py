from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite {% with x=my_dict|get_item:variable %} nos templates."""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)