

function setupButtonConfirmation(sId, sMessage){
    $('#' + sId).click(
        function(){
            var bReturn = false;
            if (confirm(sMessage) == true){
                bReturn = true;
            }
            return bReturn
        }    
    );
}

function setupSearchBoxHint(){
    $('#divSidebarSearch input:text').focus(function() {
        if ($('#divSidebarSearch input:submit').attr('disabled')) {
            $(this).val('');
            $(this).removeClass('hint');
            $('#divSidebarSearch input:submit').removeAttr('disabled'); 
        }
    });
    $('#divSidebarSearch input:text').blur(function() {
        if(!$('#divSidebarSearch input:submit').attr('disabled') && ($(this).val() == '')) {
            $(this).val('Search');
            $(this).addClass('hint');
            $('#divSidebarSearch input:submit').attr('disabled', 'disabled'); 
        }
    });
    $('#divSidebarSearch input:text').blur();
}
$(document).ready(function()
{
    setupSearchBoxHint(); 
}); 

function setupScroller(){
    
    //left right buttons
    $('.scroller a.scroll_left').click(
        function(){
            scrollScroller('left')
            return false;
        }
    );
    $('.scroller a.scroll_right').click(
        function(){
            scrollScroller('right')
            return false;
        }
    );
    
    //resize
    $(window).resize(
        function(){
            var iNewWidth = $('.scroller .scroller_wrapper').width() / 2;
            if(iNewWidth < 250){
               iNewWidth = 250;
            }
            $('.scroller .scroll_item').width(iNewWidth);
        }
    );
}

function scrollScroller(sDirection){

    //can scroll?
    var bCanScroll = true;
    var iCurrentLeft = parseInt($('.scroller .scroll_items').css('left'));
    if(sDirection == 'left' && iCurrentLeft >= 0){
        bCanScroll = false;
    }

    if(bCanScroll == true){
        //get the width of one item
        iWidth = $('.scroller .scroll_items :first-child').outerWidth() + 18;
        sWidth = ''
        if(sDirection == 'right'){
            sWidth = '-=' + iWidth
        }else{
            sWidth = '+=' + iWidth        
        }

        //scroll   
        $('.scroller .scroll_items').animate({
          left: sWidth
        }, 500);
    }
    
}

function setupIntroSlideshow(){
    $('.slide_show').cycle({
		fx: 'fade',
        speed:   1000, 
        timeout: 7000, 
        next:   '.slide_show', 
        pause:   1,
        pager: '.slide_nav',
        autostop: 0
	});
}

function setupDataViewer(){
    $('.raw_data').flexigrid({height:250});    
}

function setupCKANLink(){
    $.ajax({
        url:'http://ckan.net/api/search/resource',
        dataType:'jsonp',
        cache: true,
        data: {url: 'scraperwiki.com', all_fields: 1},
        success:function(data){
            var id = window.location.pathname.split('/')[3];
            $.each(data.results, function(index,ckan){
                if ($.inArray(id, ckan.url.split('/')) != -1){
                    $('div.metadata dl').append('<dt>CKAN:</dt><dd><a href="http://ckan.net/package/'+ckan.package_id+'" target="_blank">link</a><dd>');
                }
            });
        }
    });
}

function optiontojson(seloptsid, currsel)
{
    var result = { };
    $(seloptsid+" option").each(function(i, el) 
    {
        result[$(el).attr("value")] = $(el).text() 
        if ($(el).text() == currsel)
            result["selected"] = $(el).attr("value"); 
    }); 
    return $.toJSON(result); 
}

function setupScraperEditInPlace(wiki_type, short_name)
{
    //about
    $('#divAboutScraper').editable('admin/', {
             indicator : 'Saving...',
             tooltip   : 'Click to edit...',
             cancel    : 'Cancel',
             submit    : 'Save',
             type      : 'textarea',
             loadurl: 'raw_about_markup/',
             onblur: 'ignore',
             event: 'dblclick',
             submitdata : {short_name: short_name},
             placeholder: ''       
         });

    $('#aEditAboutScraper').click(
        function(){
             $('#divAboutScraper').dblclick();
             oHint = $('<div id="divMarkupHint" class="content_footer"><p><strong>You can use Textile markup to style the description:</strong></p><ul><li>*bold* / _italic_ / @code@</li><li>* Bulleted list item / # Numbered list item</li><li>"A link":http://www.data.gov.uk</li><li>h1. Big header / h2. Normal header</li></ul></div>');
             $('#divAboutScraper form').append(oHint);
             return false;
        }
    );

    //title
    $('#hCodeTitle').editable('admin/', {
             indicator : 'Saving...',
             tooltip   : 'Click to edit...',
             cancel    : 'Cancel',
             submit    : 'Save',
             onblur: 'ignore',
             event: 'dblclick',
             placeholder: '',             
             submitdata : {short_name: short_name}
         });
         
    $('#aEditTitle').click(
        function(){
             $('#hCodeTitle').dblclick();
             return false;
        }
    );

    // this is complex because editable div is not what you see (it's a comma separated field)
    $('#divEditTags').editable($("#adminsettagurl").val(), 
    {
        indicator : 'Saving...', tooltip:'Click to edit...', cancel:'Cancel', submit:'Save tags',
        onblur: 'ignore', event:'dblclick', placeholder:'',
        onedit: function() 
        {
            var tags = [ ]; 
            $("#divScraperTags ul.tags li a").each(function(i, el) { tags.push($(el).text()); }); 
            $(this).text(tags.join(", ")); 
        },
        onreset: function() { $('#divEditTagsControls').hide(); },
        callback: function(lis) 
        {
            $('#divScraperTags ul.tags').html(lis); 
            $('#divEditTagsControls').hide(); 
            $('#addtagmessage').css("display", ($("#divScraperTags ul.tags li a").length == 0 ? "block" : "none")); 
        }
    }); 
    $('#aEditTags').click(function()
    {
        $('#divEditTags').dblclick();
        $('#divEditTagsControls').show();
        return false;
    });
    $('#divEditTagsControls').hide();
    $('#addtagmessage').css("display", ($("#divScraperTags ul.tags li a").length == 0 ? "block" : "none")); 

    // privacy status
    $('#spnPrivacyStatusChoice').editable($("#adminprivacystatusurl").val(), 
    {
        indicator : 'Saving...', tooltip:'Click to edit...', cancel:'Cancel', submit:'Save',
        onblur: 'ignore', event:'dblclick', placeholder:'', type: 'select', 
        data: optiontojson('#optionsPrivacyStatusChoices', $('#spnPrivacyStatusChoice').text()) 
    }); 
    $('#aPrivacyStatusChoice').click(function()  {  $('#spnPrivacyStatusChoice').dblclick(); });

     //scheduler
     $('#spnRunInterval').editable('admin/', {
              indicator : 'Saving...',
              tooltip   : 'Click to edit...',
              cancel    : 'Cancel',
              submit    : 'Save',
              onblur: 'ignore',
              data   : $('#hidScheduleOptions').val(),
              type   : 'select',
              event: 'dblclick',
              placeholder: '',
              submitdata : {short_name: short_name}
          });

      $('#aEditSchedule').click(
           function(){
                sCurrent = $('#spnRunInterval').html().trim();               
                $('#spnRunInterval').dblclick();
                $('#spnRunInterval select').val(sCurrent);
                return false;
           }
       );

     //license
     $('#spnLicenseChoice').editable('admin/', {
              indicator : 'Saving...',
              tooltip   : 'Click to edit...',
              cancel    : 'Cancel',
              submit    : 'Save',
              onblur: 'ignore',
              data   : $('#hidLicenseChoices').val(),
              type   : 'select',
              event: 'dblclick',
              placeholder: '',
              submitdata : {short_name: short_name}
          });

      $('#aEditLicense').click (
           function(){
                sCurrent = $('#spnLicenseChoice').html().trim();
                $('#spnLicenseChoice').dblclick();
                $('#spnLicenseChoice select').val(sCurrent);
                return false;
           }
       );          
      

       $('#publishScraperButton').click(function(){
           $.ajax({
               url: 'admin/',
               data: {'id': 'publishScraperButton'},
               type: 'POST',
               success: function(){
                   $('#publishScraper').fadeOut();
               },
               error: function(){
                   alert("Something went wrong publishing this scraper. Please try again. If the problem continues please send a message via the feedback form.");
               }
           });
           return false;
       });
}
