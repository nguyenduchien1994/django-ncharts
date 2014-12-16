# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

from django.conf.urls import patterns, include, url

from ncharts import views
from ncharts.views import DatasetView, StaticView
# from ncharts.forms import DatasetForm
# DatasetFormPreview

# format of a pattern:
# regular expression, Python callback function [, optional dictionary [, optional_name [[
# url(regex,view,kwargs=None,name=None,prefix="")

urlpatterns = patterns('',
    url(r'^$', views.projectsPlatforms, name='projectsPlatforms'),

    url(r'^help/?$', StaticView.as_view(), { 'page': 'ncharts/help.html' } ),

    url(r'^projects/?$', views.projects, name='projects'),

    url(r'^projects/(?P<project_name>[^/]+)/?$', views.project, name='project'),

    url(r'^projects/(?P<project_name>[^/]+)/(?P<dataset_name>[^/]+)/?$', DatasetView.as_view(), name='dataset'),

    url(r'^platforms/?$', views.platforms, name='platforms'),

    # display list of projects for a platform, user selects project
    url(r'^platforms/(?P<platform_name>[^/]+)/?$', views.platform, name='platform'),

    url(r'^platforms/(?P<platform_name>[^/]+)/(?P<project_name>[^/]+)/?$', views.platformProject, name='platformProject'),

)
