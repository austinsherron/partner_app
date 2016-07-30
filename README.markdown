# Updates

## 2+Partners

I updated the architecture so that partnerships of more than 2 students are 
possible. All updates related to this change are in the 2+partners branch.

I tested this pretty rigorously, and the architecture change seems to work for groups 
of 2+, but I didn't change the logic in the Confirm/SelectPartner controllers to allow
students to form groups of more than 2. If/when you guys decide to go live with these
changes, you'll have to change some things in those controllers so that students can
form groups of more than 2. There are lots of decisions to make about how exactly to
do this (mostly UI/UX stuff), so you'll probably want to talk to Kay about it. 
Considerations include:

    + how to handle invitations
        + still just 2 person invitations?
    + how handle partner selection
        + if student sends invite to person who already has partner, and
          that person accepts, are these groups merged?
    + how to handle it on the admin side
    + reporting
        + currently, partnerships are reported in tables, so having inconsistent
          group sizes makes things a little awkward

and lots of other stuff.

There is one thing that needs to be done before this goes live: SendMail 
(src/send_mail.py)needs to be updated reflect the changes to the partnership
model. This doesn't *need* to be done before going live, but it should be done.

I haven't merged this branch into working/production, but I'm pretty sure it 
can be. Let me know if you need help merging and deploying the new version of
the app.

## Courses

All updates related to this changes are in the courses branch. They were in
the 2+partners branch, but I figured they should be separated. I reverted
theses changes in the 2+partners branch.

I've added some models/added things to other models so that multiple courses
can be supported simultanesouly. Main changes were:

    + create Course model
    + update Setting and Instructor models
    + update UI and admin/sutdent landing (MainPage/MainAdmin) controllers to 
      include a courses dropdown in the nav bar
        + clicking on a course in the dropwodwn adds the courses DB key to the 
          session
    + create course add/view/activate/deactive controllers 
    + add course add/view UIs to admin section
    + created a CourseModel class

There are, however, lots of things that still need to be done before this can go 
live. These include:

    + relating all data to courses
        + currently, all course data is related to a quarter/year combination; this
          quarter/year combination is the primary key for basically all data 
          in the app relevant to a course offering: assignments, quarters, students;
          if we want to offer multiple courses simultaneously, we need to relate
          all this data to courses, and then query it using courses
    + update model queries so that all relevat data is queried by course, not
      quarter/year (see above); this needs to be done everywhere in the app
    + making sure a list of courses is passed to each template in each controller
        + this is so the courses dropdown appears on every page
    + adding support for instructor objects
        + in the student section, the app uses student emails to look up student
          objects, to which lots of important data is tied; up to this point, no
          data has been associated with an instructor, so I haven't bothered to
          use instructor objects in the admin section; since courses need to be
          tied to instructors, support for instructor objects needs to be added
          in the admin section in the same way the student section uses student
          objects
    + adding mechanisms to manage students/instructors across courses
        + once all the above updates are made, students/instructors will
          be tied to courses, instead of quarters/years; we need to make
          sure that, when adding a roster/instructor/student to a course,
          we check to make sure that student isn't already in the database
          from another course; if he/she is, that object should be reused;
          same goes for instructors
          
Obviously, these are major updates, so you guys might decide that they aren't
worth it. If you need help making any of these updates, let me know.


