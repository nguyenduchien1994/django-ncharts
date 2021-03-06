from django import template
from ncharts import models as nc_models

register = template.Library()

@register.filter
def get_long_name(vs, v):
    """Get 'long_name' value of vs[v] """
    try:
        return vs[v]['long_name']
    except:
        return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_key_values(var_name, variables):
    for var in variables:
        if var.choice_label == var_name:
            return var

@register.filter
def make_tabs(variables, dset):
    return dset.make_tabs(variables)

@register.filter
    """Get the dictionary of years and projects from models.py"""
def make_project_tabs(projects):
    return nc_models.Project.make_tabs(projects)
