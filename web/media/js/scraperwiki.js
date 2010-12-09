function setupCodeViewer(iLineCount, scraperlanguage, codemirror_url) {
    var oCodeEditor;
    if(iLineCount < 20)
        iLineCount = 20;

    var selrangefunc = function() {
        if (!((selrange[2] == 0) && (selrange[3] == 0))){
            linehandlestart = oCodeEditor.nthLine(selrange[0] + 1); 
            linehandleend = oCodeEditor.nthLine(selrange[2] + 1); 
            oCodeEditor.selectLines(linehandlestart, selrange[1], linehandleend, selrange[3]); 
        }; 
    }; 

    $(document).ready(function(){

        var parsers = Array();
        parsers['python'] = '../contrib/python/js/parsepython.js';
        parsers['php'] = ['../contrib/php/js/tokenizephp.js', '../contrib/php/js/parsephp.js'];
        parsers['ruby'] = ['../../ruby-in-codemirror/js/tokenizeruby.js', '../../ruby-in-codemirror/js/parseruby.js'];
        parsers['html'] = ['parsexml.js', 'parsecss.js', 'tokenizejavascript.js', 'parsejavascript.js', 'parsehtmlmixed.js']; 

        var stylesheets = Array();
        stylesheets['python'] = [codemirror_url+'contrib/python/css/pythoncolors.css', '/media/css/codemirrorcolours.css'];
        stylesheets['php'] = [codemirror_url+'contrib/php/css/phpcolors.css', '/media/css/codemirrorcolours.css']; 
        stylesheets['ruby'] = ['/media/ruby-in-codemirror/css/rubycolors.css', '/media/css/codemirrorcolours.css'];
        stylesheets['html'] = [codemirror_url+'css/xmlcolors.css', codemirror_url+'css/jscolors.css', codemirror_url+'css/csscolors.css', '/media/css/codemirrorcolours.css']; 

        oCodeEditor = CodeMirror.fromTextArea("txtScraperCode", {
            parserfile: parsers[scraperlanguage],
            stylesheet: stylesheets[scraperlanguage],

            path: "/media/CodeMirror/js/",
            textWrapping: true, 
            lineNumbers: true, 
            indentUnit: 4,
            readOnly: true,
            tabMode: "spaces", 
            autoMatchParens: true,
            width: '100%',
            height: iLineCount + 'em', 
            parserConfig: {'pythonVersion': 2, 'strictErrors': true}, 

            // this is called once the codemirror window has finished initializing itself, (though happens to early, so that the selection gets deselected.  should file a bug)
            initCallback: function() { setTimeout(selrangefunc, 1000); }
        });
    });
}



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
            $(this).val('Search ScraperWiki');
            $(this).addClass('hint');
            $('#divSidebarSearch input:submit').attr('disabled', 'disabled'); 
        }
    });
    $('#divSidebarSearch input:text').blur();
}
$(document).ready(function(){ setupSearchBoxHint(); }); 

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

function setupScraperEditInPlace(wiki_type, short_name){
    
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
             submitdata : {js: 1, short_name: short_name},
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
             submitdata : {js: 1, short_name: short_name}
         });
         
    $('#aEditTitle').click(
        function(){
             $('#hCodeTitle').dblclick();
             return false;
        }
    );

    //tags
    oDummy = $('<div id="divEditTags"></div>');
    $('#divScraperTags').append(oDummy);
    $('#divEditTags').editable('admin/', {
             indicator : 'Saving...',
             tooltip   : 'Click to edit...',
             cancel    : 'Cancel',
             submit    : 'Save tags',
             onblur: 'ignore',
             event: 'dblclick',
             placeholder: '',
             loadurl: 'tags/',
             submitdata : {js: 1, short_name: short_name},
             onreset: function(){ $('#labelEditTags').hide();},
             callback: function (data){
                 //add the new tags onto the list
                 aItems = data.split(',');
                 $('#divScraperTags ul').html('');
                 for (var i=0; i < aItems.length; i++) {
                    url = '/tags/' + escape(aItems[i].trim())
                    $('#divScraperTags ul').append($('<li><a href="' + url +'">' + aItems[i].trim() + '</a></li>'))
                 };
                 //clear out the textbox for next time
                 $('#divEditTags').html('');
                 $('#labelEditTags').hide();
            }
         });
    $('#aEditTags').click (
         function(){
              $('#divEditTags').dblclick();
              $('#labelEditTags').show();
              return false;
         }
     );

     $('#labelEditTags').hide();

     //scheduler
     //alert(schedule_options.length)
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
              submitdata : {js: 1, short_name: short_name}
          });
      
      $('#aEditSchedule').click (
           function(){
                sCurrent = $('#spnRunInterval').html().trim();               
                $('#spnRunInterval').dblclick();
                $('#spnRunInterval select').val(sCurrent);
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
