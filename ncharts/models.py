# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set tabstop=8 shiftwidth=4 softtabstop=4 expandtab:

"""Models used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os, pytz, logging

from collections import OrderedDict

from django.db import models

from ncharts import netcdf, fileset, raf_database

from django.core import exceptions as dj_exc
from django.utils.translation import ugettext_lazy

import datetime

from timezone_field import TimeZoneField

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

class TimeZone(models.Model):
    """A timezone.

    Uses TimeZoneField from django-timezone-field app.
    """

    # If you add "default=pytz.utc" to TimeZoneField, then
    # makemigrations fails, reporting it can't serialize "<UTC>".
    # Haven't found a solution, so leave it off. Probably not an issue.

    # pylint thinks this class member name is too short
    # pylint: disable=invalid-name
    tz = TimeZoneField(primary_key=True)

class Project(models.Model):
    """A field project, with a unique name.

    To get all projects:
        Project.objects.all()

    To find all platforms of a project:
        Platform.objects.filter(projects__name__exact='METCRAXII')
    So we don't need this:
        platforms = models.ManyToManyField('ncharts.Platform')

    To find all datasets of a project:
        Dataset.objects.filter(project__name__exact='METCRAXII')
    So, you don't need this:
        datasets = models.ManyToManyField('ncharts.Dataset',
            related_name='datasets')
    """

    name = models.CharField(max_length=64, primary_key=True)

    location = models.CharField(max_length=256, blank=True)

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=ugettext_lazy('More detailed description of the project'))

    timezones = models.ManyToManyField(
        TimeZone,
        blank=True,
        related_name='+',
        help_text=ugettext_lazy('Supported timezones for plotting data of this project'))

    start_year = models.IntegerField()

    end_year = models.IntegerField(null=True)

    @classmethod
    def make_tabs(cls, projects):

        """A class method for creating dictionary of projects based on their start years
            and end years. The dictionary keys will be the years and the values will be 
            the projects that happen within the corresponding years. The years and projects are sorted 
            numerically and alphabetically. 

            Args: The Project class itself and the list of projects from netcdf.
            Ret: The sorted dictionary of years and projects. 

        """

        res = {}
        now = datetime.datetime.now()

        for project in projects:
            if project.end_year == None:
                project.end_year = now.year
            for year in list(range(project.start_year, project.end_year + 1)):
                if year not in res:
                    res[year] = []
                res[year].append(project)

        for year, projects in res.items():
            projects.sort(key=lambda x: x.name)

        res = OrderedDict(sorted(res.items(), key=lambda x: x[0]))

        return res

    def __str__(self):
        return self.name

class Platform(models.Model):
    """An observing platform with a unique name, deployed on one or more
    projects.

    To get all platforms:
        Platform.objects.all()
    """
    name = models.CharField(max_length=64, primary_key=True)

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=ugettext_lazy('More detailed description of the platform'))

    # This adds a platform_set attribute to Project.
    projects = models.ManyToManyField(Project)

    def __str__(self):
        # return 'Platform: %s' % self.name
        return self.name

class Variable(models.Model):
    """A variable in a dataset, used if the dataset does not have
    sufficient meta-data for its variables.
    """

    name = models.CharField(max_length=64)

    units = models.CharField(max_length=64, blank=True)

    long_name = models.CharField(max_length=256, blank=True)

class Dataset(models.Model):
    """A dataset, whose name should be unique within a project.

    Tried making this an abstract base class in django.
    From the django doc on abstract base classes of models:
        This model will then not be used to create any database table.
        Instead, when it is used as a base class for other models,
        its fields will be added to those of the child class. It is
        an error to have fields in the abstract base class with the
        same name as those in the child (and Django will raise an exception).

    However, a Dataset is a ForeignKey of a ClientState, and
    it appears an abstract model cannot be a ForeignKey. So we
    use the Multi-table inheritance in django.

    Then, to determine if a Dataset is a FileDataset, do

    try:
        x = dataset.filedataset
    except FileDataset.DoesNotExist as exc:
        pass

    To find all datasets of a project:
        Dataset.objects.filter(project__name__exact='METCRAXII')

    To find all datasets of a platform:
        Dataset.objects.filter(platforms__name__exact="ISFS")

    To find all datasets of a project and platform:
        Dataset.objects.filter(
            platforms__name__exact=platform_name).filter(
                project__name__exact=project_name)

    Don't add __init__ method, instead add @classmethod create() or a
    custom Manager.
    See https://docs.djangoproject.com/en/dev/ref/models/instances/

    For other instance variables, just set them in instance methods.
    """

    # class Meta:
    #     abstract = False

    name = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('The name of a dataset should be unique within a project'))

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=ugettext_lazy('More detailed description of a dataset'))

    url = models.URLField(
        blank=True,
        max_length=200,
        help_text=ugettext_lazy('The URL that specifies the complete project dataset'))

    status = models.CharField(
        blank=True,
        max_length=256,
        help_text=ugettext_lazy('Current status of the project dataset'))

    # This adds a dataset_set attribute to Project
    project = models.ForeignKey(
        Project,
        help_text=ugettext_lazy('A dataset is associated with one project'))

    # This adds a dataset_set attribute to Platform
    platforms = models.ManyToManyField(
        Platform,
        help_text=ugettext_lazy('A dataset is associated with one or more platforms'))

    timezones = models.ManyToManyField(
        TimeZone,
        help_text=ugettext_lazy('Overrides the timezones of the project'))

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    location = models.CharField(
        max_length=256, blank=True,
        help_text=ugettext_lazy("Location for dataset if different than for project"))

    dset_type = models.CharField(
        blank=True,
        max_length=16,
        help_text=ugettext_lazy('Type of dataset: time-series, sounding'))

    # '+' tells django not to create a backwards relation from
    # Variable to Dataset
    variables = models.ManyToManyField(
        Variable, related_name='+')

    # netcdf_time_series, raf_postgres
    # dstype = models.CharField(max_length=64, blank=True)

    def __str__(self):
        # return 'Dataset: %s' % (self.name,)
        return self.name

    def add_platform(self, platform):
        """When one does a dataset.platforms.add(isfs), also do
        project.platforms.add(isfs).
        """
        self.platforms.add(platform)
        platform.projects.add(self.project)

    def get_start_time(self):
        '''
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is
        None, or if d.tzinfo is not None but d.tzinfo.utcoffset(d)
        returns None, d is naive.
        '''

        # _logger.debug("Dataset get_start_time, start_time=%s",
        #    self.start_time.isoformat())
        if self.start_time.tzinfo == None or \
                self.start_time.tzinfo.utcoffset(self.start_time) == None:
            self.start_time = pytz.utc.localize(self.start_time)
            _logger.debug(
                "Dataset localized start_time: %s",
                self.start_time.isoformat())

        return self.start_time

    def get_end_time(self):
        """
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is None,
        or if d.tzinfo is not None but d.tzinfo.utcoffset(d) returns None,
        d is naive.
        """

        # _logger.debug("Dataset get_end_time, end_time=%s",
        #       self.end_time.isoformat())
        if self.end_time.tzinfo == None or \
                self.end_time.tzinfo.utcoffset(self.end_time) == None:
            self.end_time = pytz.utc.localize(self.end_time)
            _logger.debug(
                "Dataset localized end_time: %s",
                self.end_time.isoformat())

        return self.end_time

    def alphabetic_tabs(self, variables):
        """Create a dictionary of tabs for the elements in variables.

        This is so that a large number of checkbox widgets for the
        selection of data variables to be plotted can be split into
        tabbed panes.

        The tab names can be created from the first character of the
        variable names, or in a platform-dependent way, by a
        category determined from the variable name.

        Args:
            variables: a django.forms.forms.BoundField, such as
            from form['variables'], where form is an instance
            of ncharts.forms.DataSelectionForm, which has a
            class member named variables of type
            forms.MultipleChoiceField. The variables have been
            alphabetically sorted prior to this call.

        Each element returned by iterating over variables is
        a django.forms.widgets.CheckboxChoiceInput.
        An instance of CheckboxChoiceInput has a choice_label
        attribute containing the label part of the choice tuple,
        (the variable name) and a tab attribute, which when
        rendered in a template, creates the checkbox html.

        References to these widgets are copied into lists
        under each tab.
        """

        nvars = len(variables)

        tabs = OrderedDict()

        for var in iter(variables):
            vname = var.choice_label
            char1 = vname[0].upper()
            if not char1 in tabs:
                tabs[char1] = {"variables":[]}
            tabs[char1]["variables"].append(var)

        # Combine neighboring tabs if they each contain
        # fewer than tab_limit elements
        tab_limit = 10
        comb_tabs = OrderedDict()
        for tab, vals in tabs.items():

            # Sort by first letter
            # vals.sort(key=lambda x: x.choice_label.lower())

            # pylint thinks ctab could be used before assignment
            # pylint: disable=used-before-assignment
            if len(comb_tabs) == 0 or \
                    len(comb_tabs[ctab]["variables"]) > tab_limit or \
                    len(vals["variables"]) > tab_limit:
                ctab = tab
                comb_tabs[ctab] = vals
            else:
                nctab = ctab[0] + "-" + tab
                if not nctab in comb_tabs:
                    comb_tabs[nctab] = {"variables":[]}
                comb_tabs[nctab]["variables"] = comb_tabs[ctab]["variables"] + vals["variables"]
                del comb_tabs[ctab]
                ctab = nctab

        # Double check that we didn't lose any variables
        nres = 0
        for tab, vals in comb_tabs.items():
            nres += len(vals["variables"])

        if nres != nvars:
            _logger.error("%d variables unaccounted for in building tabs", (nvars - nres))
        return comb_tabs

    def isfs_tabs(self, variables):
        """Create a tabs dictionary for ISFS variables

        Args:
            variables: a django.forms.forms.BoundField, such as
            from form['variables'], where form is an instance
            of ncharts.forms.DataSelectionForm, which has a
            class member named variables of type
            forms.MultipleChoiceField. The variables have been
            alphabetically sorted prior to this call.
        """

        tabs = {}

        tabs["Met"] = {"tooltip":"Meteorological Variables", "variables":[]}
        tabs["Power"] = {"tooltip":"Battery and Solar Power", "variables":[]}
        tabs["Rad"] = {"tooltip":"Radiation Variables", "variables":[]}
        tabs["Soil"] = {"tooltip":"Soil Variables", "variables":[]}
        tabs["3dWind"] = {"tooltip":"3D Wind Variables", "variables":[]}
        tabs["Scalars"] = {"tooltip":"Fast Scalars Variables", "variables":[]}
        tabs["Others"] = {"tooltip":"Other Variables", "variables":[]}
        tabs["2ndMoments"] = {"tooltip":"2nd Moments Variables", "variables":[]}
        tabs["3rdMoments"] = {"tooltip":"3rd Moments Variables", "variables":[]}
        tabs["4thMoments"] = {"tooltip":"4th Moments Variables", "variables":[]}

        met_list = ["T", "RH", "P", "Spd", "Spd_max", "Dir", "U", "V", "Ifan"]
        pow_list = ["Vbatt", "Tbatt", "Iload", "Icharge", "Vmote"]
        rad_list = ["Rnet", "Rsw", "Rlw", "Rpile", "Rpar", "Tcase", "Tdome", "Wetness"]
        soil_list = ["Tsoil", "dTsoil_dt", "Qsoil", "Gsoil", "Vheat", "Vpile", \
            "Tau63", "Lambdasoil", "asoil", "Cvsoil", "Gsfc"]
        wind_list = ["u", "v", "w", "ldiag", "diagbits", "spd", "spd_max", "dir"]
        scalars_list = ["tc", "t", "h2o", "co2", "kh2o", "o3", "q", "mr", "irgadiag", "p"]

        for var in iter(variables):
            start_field = var.choice_label.split(".", 1)[0]
            quote_num = start_field.count("'")
            if quote_num == 0:
                if start_field in met_list:
                    tabs["Met"]["variables"].append(var)
                elif start_field in pow_list:
                    tabs["Power"]["variables"].append(var)
                elif start_field in rad_list:
                    tabs["Rad"]["variables"].append(var)
                elif start_field in soil_list:
                    tabs["Soil"]["variables"].append(var)
                elif start_field in wind_list:
                    tabs["3dWind"]["variables"].append(var)
                elif start_field in scalars_list:
                    tabs["Scalars"]["variables"].append(var)
                else:
                    tabs["Others"]["variables"].append(var)
            elif quote_num == 2:
                tabs["2ndMoments"]["variables"].append(var)
            elif quote_num == 3:
                tabs["3rdMoments"]["variables"].append(var)
            elif quote_num == 4:
                tabs["4thMoments"]["variables"].append(var)
            else:
                tabs["Others"]["variables"].append(var)

        tabs = {key: value for key, value in tabs.items() if value["variables"]}
        tabs = OrderedDict(sorted(tabs.items(), key=lambda x: x[0]))

        return tabs

    def make_tabs(self, variables):

        """Select the correct tabbing method for the corresponding platform.
            If the dataset if of ISFS platform, the isfs_tabs method is used.
            Else, the alphabetic_tabs method is used.

        """

        is_isfs = False

        for plat in self.platforms.all():
            if plat.name == "ISFS":
                is_isfs = True

        if is_isfs:
            return self.isfs_tabs(variables)
        else:
            return self.alphabetic_tabs(variables)

class FileDataset(Dataset):
    """A Dataset consisting of a set of similarly named files.

    """

    directory = models.CharField(
        max_length=256,
        help_text=ugettext_lazy('Path to the directory containing the files for this dataset'))

    # format of file names, often containing timedate descriptors: %Y etc
    filenames = models.CharField(
        max_length=256,
        help_text=ugettext_lazy('Format of file names, often containing ' \
            'timedate descriptors such as %Y'))

    def get_fileset(self):
        """Return a fileset.Fileset corresponding to this
        FileDataset.
        """
        return fileset.Fileset(
            os.path.join(self.directory, self.filenames))

    def get_netcdf_dataset(self):
        """Return the netcdf.NetCDFDataset corresponding to this
        FileDataset.
        """
        return netcdf.NetCDFDataset(
            os.path.join(self.directory, self.filenames),
            self.get_start_time(), self.get_end_time())

    def get_variables(self):
        """Return the time series variable names of this dataset.

        Raises:
            exception.NoDataFoundException
        """
        if len(self.variables.values()) > 0:
            res = {}
            for var in self.variables.all():
                res[var.name] = \
                    {"units": var.units, "long_name": var.long_name}
            return res

        ncdset = self.get_netcdf_dataset()

        return ncdset.get_variables()

    def get_series_tuples(
            self,
            series_name_fmt="",
            start_time=pytz.utc.localize(datetime.datetime.min),
            end_time=pytz.utc.localize(datetime.datetime.max)):
        """Get the names of the series between the start and end times.
        """
        if not self.dset_type == "sounding":
            return []

        files = self.get_fileset().scan(start_time, end_time)

        # series names, formatted from the time of the file.
        # The scan function returns the file previous to start_time.
        # Remove that.
        return [(f.time.strftime(series_name_fmt), f.time.timestamp()) for f in files \
                if f.time >= start_time]

    def get_series_names(
            self,
            series_name_fmt="",
            start_time=pytz.utc.localize(datetime.datetime.min),
            end_time=pytz.utc.localize(datetime.datetime.max)):
        """Get the names of the series between the start and end times.
        """
        if not self.dset_type == "sounding":
            return []

        files = self.get_fileset().scan(start_time, end_time)

        # series names, formatted from the time of the file.
        # The scan function returns the file previous to start_time.
        # Remove that.
        return [f.time.strftime(series_name_fmt) for f in files \
                if f.time >= start_time]

class DBDataset(Dataset):
    """A Dataset whose contents are in a database.

    """

    dbname = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('Database name'))

    host = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('Database host'))

    user = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('Database user'))

    password = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('Database password'))

    port = models.IntegerField(
        default=5432,
        help_text=ugettext_lazy('Database port number, defaults to 5432'))

    table = models.CharField(
        max_length=128,
        help_text=ugettext_lazy('Database table name'))


    def get_connection(self):
        """Return a database connection for this DBDataset.

        Raises:
            exception.NoDataFoundException
        """

        return raf_database.RAFDatabase(
            database=self.dbname,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password)

    def get_variables(self):
        """Return the time series variables in this DBDataset.

        Raises:
            exception.NoDataFoundException
        """
        return self.get_connection().get_variables()

    def get_start_time(self):
        """
        Raises:
            exception.NoDataFoundException
        """
        return self.get_connection().get_start_time()

def validate_positive(value):
    """Validator."""
    if value <= 0:
        raise dj_exc.ValidationError('%s is not greater than zero' % value)

class VariableTimes(models.Model):
    """Times of data sent to a client.

    """

    # blank=False means it is required
    name = models.CharField(max_length=64, blank=False)

    last_ok = models.IntegerField(blank=False)

    last = models.IntegerField(blank=False)


class ClientState(models.Model):
    """Current state of an nchart client.

    The automatic primary key 'id' of an instance of this model
    is stored in the user's session by project and dataset name,
    and so when a user returns to view this dataset, their
    previous state is provided.
    """

    variables = models.TextField(blank=True)  # list of variables, stringified by json

    # Variable on sounding Y axis
    yvariable = models.TextField(blank=True)

    # The selected Dataset. Dataset is a base class for several
    # types of Datasets. Since it is used here as a ForeignKey,
    # it cannot be abstract.
    # related_name='+' tells django not to create a backwards relation
    # from Dataset to ClientState, which we don't need.
    dataset = models.ForeignKey(Dataset, related_name='+')

    timezone = TimeZoneField(blank=False)

    start_time = models.DateTimeField()

    time_length = models.FloatField(
        blank=False, validators=[validate_positive],
        default=datetime.timedelta(days=1).total_seconds())

    track_real_time = models.BooleanField(default=False)

    data_times = models.ManyToManyField(
        VariableTimes,
        blank=True,
        related_name='+')

    # list of sounding series, stringified by json
    soundings = models.TextField(blank=True)

    def __str__(self):
        return 'ClientState for dataset: %s' % (self.dataset.name)

    def clean(self):
        if self.start_time < self.dataset.get_start_time():
            raise dj_exc.ValidationError(
                "start_time is earlier than dataset.start_time")
        # if self.end_time > self.dataset.end_time:
        #     raise dj_exc.ValidationError(
        #       "end_time is earlier than dataset.end_time")
        # if self.start_time >= self.end_time:
        #     raise dj_exc.ValidationError(
        #       "start_time is not earlier than end_time")

        if self.time_length <= 0:
            raise dj_exc.ValidationError("time_length is not positive")

    def save_data_times(self, vname, time_last_ok, time_last):
        """Save the times associated with the last chunk of data sent to this client.
        """
        try:
            vart = self.data_times.get(name=vname)
            vart.last_ok = time_last_ok
            vart.last = time_last
            vart.save()
        except VariableTimes.DoesNotExist:
            vart = VariableTimes.objects.create(
                name=vname, last_ok=time_last_ok, last=time_last)
            self.data_times.add(vart)

    def get_data_times(self, vname):
        """Fetch the times associated with the last chunk of data sent to this client.
        """
        try:
            vart = self.data_times.get(name=vname)
            return [vart.last_ok, vart.last]
        except VariableTimes.DoesNotExist:
            return [None, None]

