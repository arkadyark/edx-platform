"""
Get call stacks of Model Class
in three cases-
1. QuerySet API
2. save()
3. delete()

classes:
CallStackManager -  stores all stacks in global dictionary and logs
CallStackMixin - used for Model save(), and delete() method

Functions:
capture_call_stack - global function used to store call stack

Decorators:
donottrack - mainly for the places where we know the calls. This decorator will let us not to track in specified cases
How to use-
1. Import following in the file where class to be tracked resides
    from openedx.core.lib.call_stack_manager import CallStackManager, CallStackMixin
2. Override objects of default manager by writing following in any model class which you want to track-
    objects = CallStackManager()
3. For tracking Save and Delete events-
    Use mixin called "CallStackMixin"
    For ex.
        class StudentModule(CallStackMixin, models.Model):

Note -
1.Format for STACK_BOOK
{
    "modelclass1":
        [[(frame 1),(frame 2)],
         [(frame 11),(frame21)]]
    "modelclass2":
        [[(frame 3),(frame 4)],
         [(frame 6),(frame 5)]]

}
where frame is a tuple of
(file path, Line Number, Context)
"""

import logging
import traceback
import re
import collections
from django.db.models import Manager

log = logging.getLogger(__name__)

# Module Level variables
# dictionary which stores call stacks.
# { "ModelClasses" : [ListOfFrames]}
# Frames - ('FilePath','LineNumber','Context')
# ex. {"<class 'courseware.models.StudentModule'>" : [[(file,line number,context),(---,---,---)],
#                                                     [(file,line number,context),(---,---,---)]]}
STACK_BOOK = collections.defaultdict(list)

# filter to trickle down call stacks
EXCLUDE = ['^.*python2.7.*$', '^.*call_stack_manager.*$', '^.*<exec_function>.*$', '^.*exec_code_object.*$']
REGULAR_EXPS = [re.compile(x) for x in EXCLUDE]

TRACK_FLAG = True


def capture_call_stack(current_model):
    """
    stores customised call stacks in global dictionary `STACK_BOOK`, and logs it.

    Arguments:
    current_model - Name of the model class
    """

    # holds temporary callstack
    temp_call_stack = [(frame.split(',')[0].strip()[6:-1],
                        frame.split(',')[1].strip()[6:],
                        frame.split(',')[2].strip()[3:])
                       for frame in [stack.replace("\n", "") for stack in traceback.format_stack()]
                       if not any(reg.match(frame) for reg in REGULAR_EXPS)]

    # avoid duplication.
    if temp_call_stack not in STACK_BOOK[current_model]:
        STACK_BOOK[current_model].append(temp_call_stack)
        log.info("logging new call in global stack book, for %s", current_model)
        log.info(STACK_BOOK)


class CallStackMixin(object):
    """
    A mixin class for getting call stacks when Save() and Delete() methods are called
    """
    def save(self, *args, **kwargs):
        """
        Logs before save and overrides respective model API save()
        """
        capture_call_stack(str(type(self)))
        return super(CallStackMixin, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Logs before delete and overrides respective model API delete()
        """
        capture_call_stack(str(type(self)))
        return super(CallStackMixin, self).delete(*args, **kwargs)


class CallStackManager(Manager):
    """
    gets call stacks of model classes
    """
    def get_query_set(self):
        """
        overriding the default queryset API methods
        """
        capture_call_stack(str(self.model))
        return super(CallStackManager, self).get_query_set()


def donottrack(func):
    """
    function decorator which deals with toggling call stacks
    How to use -
    1. Just Import following
        import from openedx.core.lib.call_stack_manager import donottrack
    :param func: Argument function
    :return: wrapped function
    """
    def wrapper_func(*args, **kwargs):
        """
        :return: wrapped function after setting TRACE_FLAG as True
        """
        global TRACK_FLAG  # pylint: disable-msg=W0603
        TRACK_FLAG = False
        func(*args, **kwargs)
        TRACK_FLAG = True
    return wrapper_func
