/*
	This is the javascript source for the when-to-meet style availability table that we tried to implement
	But had to sideline due to it causing instability for users.
	
	It essentially constructs an HTML table where the user can select their availablity,
	Then extracts that availablity as a string of 0 and 1, representing unavailable 1/2 
	hour blocks, and available 1/2 hour blocks respectively.
*/

//Initalize constants
ROW_NUM = 30;
COL_NUM = 5;
SYMB_AVAIL = "✓";
SYMB_UNAVAIL = "✕";
COL_AVAIL = "#22aa44";
COL_UNAVAIL = "#bbb";
STRING_EMPTY = "";

//Initialize a string to represent the table empty (completely unavailable)
for (var i = 0; i < ROW_NUM*COL_NUM; i++)
	STRING_EMPTY += "0";

//Build the HTML of the table itself
//It can take a string of the existing availablity, but defaults to an empty table
function buildGrid(cols, rows, string_availability = STRING_EMPTY) {
	var tableMarkup = "<tr><th></th><th>M</th><th>Tu</th><th>W</th><th>Th</th><th>F</th></tr>";
	time = ["08:00AM","08:30AM","09:00AM","09:30AM","10:00AM","10:30AM","11:00AM","11:30AM","12:00PM","12:30PM",
	"01:00PM","01:30PM","02:00PM","02:30PM","03:00PM","03:30PM","04:00PM","04:30PM","05:00PM","05:30PM",
	"06:00PM","06:30PM","07:00PM","07:30PM","08:00PM","08:30PM","09:00PM","09:30PM","10:00PM","10:30PM"];
	
	var index = 0;
	for (x = 0; x < rows; x++) {
		tableMarkup += "<tr><th>"+time[x]+"</th>";
		for (y = 0; y < cols; y++) {
			if (string_availability[index] == 1)
				tableMarkup += "<td style='color:" + COL_UNAVAIL + "; background: "+COL_AVAIL+"'>" + SYMB_AVAIL + "</td>";
			else
				tableMarkup += "<td style='color:" + COL_UNAVAIL + "'>" + SYMB_UNAVAIL + "</td>";
			index++;
		}
		tableMarkup += "</tr>";	
	}

	$("#drawing-table").html(tableMarkup)

};

//Extract the availability string from the HTML availability table
function getGridString(cols, rows)
{
	var tableMarkup = $("#drawing-table").html();
	var index = 0;
	var result = "";
	while(true)
	{
		index = tableMarkup.indexOf("</td>", index);
		if (index == -1)
			break;
		if (tableMarkup[index-1] == SYMB_AVAIL)
			result += "1";
		else
			result += "0";
		index++;
	}
	return result;
}

//Set an invisible field to the availability string
function updateGrid(cols, rows) {
	$('#availability_string_out').html(getGridString(cols,rows));
}

//Clears the table to all 0 (unavailable)
function clearSelection()
{
 if (window.getSelection) {window.getSelection().removeAllRanges();}
 else if (document.selection) {document.selection.empty();}
}

$(function() {
	
	// Variable Setup
	var cols = COL_NUM,
	    rows = ROW_NUM,
	    curColor = COL_AVAIL,
	    mouseDownState = false,
	    eraseState = false,
	    tracingMode = false,
	    prevColor = "",
	    $el;
	 
	 
	av_string = $('#availability_string_in').html();
	// Inital Build of Table  
	buildGrid(cols, rows, av_string);
	
	// Clearing the Design
	$("#clear").on( "click", function() {
		rows = ROW_NUM
		cols = COL_NUM
		buildGrid(cols, rows);
		updateGrid(cols, rows);
	});
	
	// Drawing functionality
	$("#drawing-table").delegate("td", "mousedown", function() {
		mouseDownState = true;
		eraseState = $("input[name='draw']:checked").val()=="erase";
		clearSelection()
		$el = $(this);
	    if (eraseState) {
	    	$el.removeAttr("style");
			$el.html(SYMB_UNAVAIL);
	    } else {
	    	$el.css("background", curColor);
			$el.html(SYMB_AVAIL);
	    }
		$el.css("color", COL_UNAVAIL);
	}).delegate("td", "mouseenter", function() {
		if (mouseDownState) {
			clearSelection()
			$el = $(this);
		    if (eraseState) {
		    	$el.removeAttr("style");
				$el.html(SYMB_UNAVAIL);
		    } else {
		    
		    	// DRAWING ACTION
		    	$el.css("background", curColor);
				$el.html(SYMB_AVAIL);
		    }
			$el.css("color", COL_UNAVAIL);
		}
	});
	$("html").bind("mouseup", function() {
		clearSelection()
		if (mouseDownState)
		{
			mouseDownState = false;
			updateGrid(cols, rows);
		}
	});
	
	// Color selection swatches
	$("#color-selector").delegate(".color", "click", function() {
		
		$el = $(this);
		var pulledVal = $el.attr("data-color");
		
		if (pulledVal == 'eraser') {
			eraseState = true;
		} else {
			eraseState = false;
			curColor = pulledVal;
		}
		
		$(".color").removeClass("selected");
		$(this).addClass("selected");
	});
});