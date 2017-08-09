$(document).ready(function()
{
	function tableToCSV($table, filename)
	{
		var rowSep = '"\r\n"';
		var colSep = '","';
		var $rows = $table.find('tr:has(td),tr:has(th)');
		
		//Convert table to CSV string
		csv = '"' + $rows.map(
		function(r, row)
			{
			var $row = $(row);
			$cols = $row.find('td,th');
			return $cols.map(function(c,col)
			{
				var $col = $(col);
				
				//Replace inline quotes with double-quotes
				return $col.text().replace(/"/g, '""');
				
			}).get().join(colSep);
		}).get().join(rowSep)
		+ '"';
		
		//Download the CSV file
		//DOES NOT WORK ON INTERNET EXPLORER 10+ OR EDGE
		//FIX THIS SO IT IS UNIVESALLY COMPATABLE
		if (window.Blob && window.URL)
		{
			// HTML5 Blob        
			var blob = new Blob([csv],{type: 'text/csv;charset=utf-8'});
			var csvUrl = URL.createObjectURL(blob);
			$(this)
			.attr({'download': filename,'href': csvUrl});
		}
		else
		{
			// Data URI
			var csvData = 'data:application/csv;charset=utf-8,' + encodeURIComponent(csv);
			$(this).attr({'download': filename,'href': csvData,'target': '_blank'});
		}
	}

	
	//Download the csv when a link with the .export_csv class is clicked
	//Other attributes in the link specify the filename and id of the table to be converted
	$(".export_csv").on('click', function(event) 
	{
		//The ID of the table to be converted into a csv file is stored in the table_name attribute of the button
		var tableId = $(".export_csv").attr("table_name");
		//The filename of the csv file is stored in the csv_filename attribute of the button
		var filename = $(".export_csv").attr("csv_filename");
		var args = [$('#' + tableId), filename];
		tableToCSV.apply(this, args);
	});
});
/*
Code is modified from the table-to-csv output code posted here by Terry Young under the Creative Commons license.
https://stackoverflow.com/questions/16078544/export-to-csv-using-jquery-and-html
*/