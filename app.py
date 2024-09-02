import dash
from flask import Flask, jsonify, request
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State, ALL
import dash_cytoscape as cyto
import mongodb_utils
import mysql_utils
import neo4j_utils
import requests
import plotly.graph_objs as go
import random

from wordcloud import WordCloud
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Helper to generate wordcloud
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')

    # Save the word cloud image in memory
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    return f"data:image/png;base64,{img_str}"

# Helper to generate wordcloud from frequencies
def generate_wordcloud_from_frequencies(word_frequencies):
    wordcloud = WordCloud(width=850, height=380, background_color='white').generate_from_frequencies(word_frequencies)
    image = BytesIO()
    wordcloud.to_image().save(image, format='PNG')
    image.seek(0)
    return 'data:image/png;base64,' + base64.b64encode(image.read()).decode('utf-8')

# Create a dash application
server = Flask(__name__)
app = Dash(__name__, server=server)
app.scripts.config.serve_locally = True  # Ensure local assets are served

# Ensure mongodb indexes are created
mongodb_utils.create_indexes()

# Add a title to the layout
app.layout = html.Div([
    html.H1('Academic Faculty and Research Insight Dashboard', style={'textAlign': 'center', 'color': '#2c3e50'}),
    html.Div([
        # Searchbar
        html.Div([
            dcc.Input(
                id='search-bar',
                type='text',
                placeholder='Search name or title...',
                style={'margin-right': '10px', 'width': '80%', 'height': '40px', 'fontSize': '18px', 'border': '1px solid #ccc', 'border-radius': '5px'}
            ),
            html.Button('Search', id='search-button', style={'height': '40px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'})
        ], style={'display': 'flex', 'align-items': 'center', 'width': '45%'}),

        # Tags
        html.Div([
            html.Div([
                html.Button('Faculty', id='faculty-button', style={'display': 'block', 'margin-bottom': '5px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'}),
                html.Button('Affiliations', id='affiliations-button', style={'display': 'block', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'}),
                # Dropdown
                dcc.Dropdown(
                    id='keyword-dropdown',
                    options=[
                        {'label': 'Massachusetts Institute of Technology (MIT)', 'value': 'Massachusetts Institute of Technology'},
                        {'label': 'Stanford University', 'value': 'Stanford University'},
                        {'label': 'Carnegie Mellon University', 'value': 'Carnegie Mellon University'},
                        {'label': 'University of California--Berkeley', 'value': 'University of California--Berkeley'},
                        {'label': 'California Institute of Technology (Caltech)', 'value': 'California Institute of Technology'},
                        {'label': 'University of Illinois at Urbana-Champaign', 'value': 'University of illinois at Urbana Champaign'},
                        {'label': 'University of Washington', 'value': 'University of Washington'},
                        {'label': 'University of Texas at Austin', 'value': 'University of Texas at Austin'},
                        {'label': 'Princeton University', 'value': 'Princeton University'},
                        {'label': 'University of California--Los Angeles (UCLA)', 'value': 'University of California--Los Angeles'}
                    ],
                    placeholder='Select a university',
                    style={'margin-top': '5px', 'width': '100%', 'border': '1px solid #ccc', 'border-radius': '5px'}
                ),
                html.Div([
                    html.Div(id='publication-keywords-input', style={'margin-top': '10px'}, children=[
                        dcc.Input(
                            id='school-name-keyword-input',
                            type='text',
                            placeholder='Enter school name...',
                            style={'margin-right': '10px', 'width': '80%', 'height': '30px', 'fontSize': '14px', 'border': '1px solid #ccc', 'border-radius': '5px'}
                        ),
                    ]),
                    html.Button('Get Top Keywords', id='top-keywords-button', style={'display': 'block', 'margin-top': '5px', 'margin-bottom': '5px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'}),
                    html.Div(id='top-keywords-display', style={'margin-top': '10px'})
                ]),
                html.Div([
                    html.Div(id='krc-input', style={'margin-top': '10px'}, children=[
                        dcc.Input(
                            id='school-name-krc-input',
                            type='text',
                            placeholder='Enter school name...',
                            style={'margin-right': '10px', 'width': '80%', 'height': '30px', 'fontSize': '14px', 'border': '1px solid #ccc', 'border-radius': '5px'}
                        ),
                        dcc.Input(
                            id='keyword-krc-input',
                            type='text',
                            placeholder='Enter keyword...',
                            style={'margin-right': '10px', 'width': '80%', 'height': '30px', 'fontSize': '14px', 'border': '1px solid #ccc', 'border-radius': '5px'}
                        )
                    ]),
                    html.Button('Calculate KRC', id='calculate-krc-button-action', style={'display': 'block', 'margin-top': '5px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'})
                ]),
            ], style={'padding': '10px', 'width': '48%', 'background-color': '#ecf0f1', 'border': '1px solid #ccc', 'border-radius': '10px'}),

            # Summary box
            html.Div(id='summary-box', style={
                'border': '2px solid black',
                'padding': '20px',
                'width': '48%',
                'height': '300px',
                'overflow-y': 'auto',
                'border-radius': '10px',
                'box-sizing': 'border-box',
                'background-color': '#f9f9f9'
            })
        ], style={'margin-left': '20px', 'margin-top': '20px', 'width': '45%', 'display': 'flex', 'justify-content': 'space-between', 'background-color': '#f0f0f0', 'border': '1px solid #ccc', 'border-radius': '5px'})
    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

    # Sliders and info box
    html.Div([
        # Range Slider and Favorite Button
        html.Div([
            html.Div([
                dcc.RangeSlider(
                    id='year-range-slider',
                    min=1900,
                    max=2023,
                    step=1,
                    value=[1900, 2023],
                    marks={i: f'{i}' for i in range(1900, 2024, 10)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
                html.Div([
                    html.Span('Year Start', style={'float': 'left'}),
                    html.Span('Year End', style={'float': 'right'})
                ], style={'display': 'flex', 'justify-content': 'space-between'})
            ], style={'flex': '1', 'width': '70%'}),

            # Favorite button
            html.Button('Show Favorites', id='show-favorites-button', style={'height': '40px', 'margin-left': '360px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px'})
        ], style={'display': 'flex', 'align-items': 'center', 'margin-top': '20px', 'justify-content': 'space-between'})
    ]),

    html.Div([
        # Create a place to display results
        html.Div(id='results-display', style={
            'margin-top': '20px',
            'border': '2px solid black',
            'padding': '20px',
            'width': '65%',
            'height': '300px',
            'overflow-y': 'auto',
            'border-radius': '10px',
            'box-sizing': 'border-box',
            'background-color': '#f9f9f9'
        }),

        # Favorites display
        html.Div([
            html.Div(id='favorites-display', style={
                'margin-top': '20px',
                'border': '2px solid black',
                'padding': '20px',
                # 'width': '350px',
                'height': '300px',
                'overflow-y': 'auto',
                'border-radius': '10px',
                'box-sizing': 'border-box',
                'background-color': '#f9f9f9'
            })
        ], style={'margin-left': '20px', 'width': '30%'})
    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

    html.Div([
        html.H2('Research and Publication Insight of Selected Faculty', style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.Div([
            dcc.Input(
                id='faculty-id-input',
                type='number',
                placeholder='Enter Faculty ID',
                style={'margin-right': '10px', 'width': '200px', 'height': '40px', 'fontSize': '18px', 'border': '1px solid #ccc', 'border-radius': '5px', 'margin-top': '10px'}
            ),
            html.Button('Generate Insight', id='show-publications-button', style={'height': '40px', 'background-color': '#3498db', 'color': 'white', 'border': 'none', 'border-radius': '5px', 'margin-top': '10px'})
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '20px', 'justify-content': 'center'})
    ], style={'margin-top': '20px', 'border': '1px solid #ccc', 'border-radius': '10px'}),

    # Top Publication Graph and Wordcloud
    html.Div([
        # Container for Top Publication Graph
        html.Div([
            html.H3('Top Publications', style={'textAlign': 'center', 'color': '#2c3e50'}),
            dcc.Graph(id='top-cited-publications-graph')
        ], style={'width': '48%', 'padding': '10px', 'background-color': '#ecf0f1', 'border': '1px solid #ccc', 'border-radius': '10px'}),

        # Container for Word Cloud
        html.Div([
            html.H3('Research Topics', style={'textAlign': 'center', 'color': '#2c3e50'}),
            html.Div([
                html.Img(id='wordcloud-image', style={'margin-top': '20px', 'width': '100%'})
            ])
        ], style={'width': '48%', 'padding': '10px', 'background-color': '#ecf0f1', 'border': '1px solid #ccc', 'border-radius': '10px'})
    ], style={'width': '100%', 'display': 'flex', 'justify-content': 'space-between'}),

    # Network Graph
    html.Div([
        html.H3('Publication Collaboration Network', style={'textAlign': 'center', 'color': '#2c3e50'}),
        cyto.Cytoscape(
            id='network-graph',
            layout={'name': 'cose'},  # Changed layout to 'cose' for better node distribution
            style={'width': '100%', 'height': '600px', 'border-radius': '10px', 'border': '1px solid #ccc', 'background-color': '#ecf0f1'},
            elements=[],
            stylesheet=[
                {
                    'selector': 'node',
                    'style': {
                        'background-image': 'data(image)',  # Path to your image
                        'background-fit': 'cover',
                        'width': '80px',
                        'height': '80px',
                        'label': 'data(label)',
                        'background-color': 'data(color)'
                    }
                },
                {
                    'selector': 'edge',
                    'style': {
                        'label': 'data(label)',
                        'text-rotation': 'autorotate',
                        'text-margin-x': '0px',
                        'text-margin-y': '-10px',
                        'width': 'data(weight)',
                        'line-color': 'data(color)'
                    }
                }
            ]
        )
    ], style={'background-color': '#f0f0f0', 'border': '1px solid #ccc', 'border-radius': '10px'})
], style={'padding': '0 100px', 'fontFamily': 'Arial, sans-serif', 'background-color': '#f9f9f9'})



# Helper function to Fetch favorite faculty and publications from the database
def show_favorite():
    favorite_faculty = mysql_utils.get_favorite_faculty()
    favorite_publications = mysql_utils.get_favorite_publications()

    favorite_elements = []
    if favorite_faculty:
        for faculty_result in favorite_faculty:
            favorite_elements.append(html.Div([
                html.H4(f"{faculty_result['name']}", style={'display': 'inline-block', 'margin-right': '10px'}),
                html.Button(
                    'Remove from Favorites', 
                    id={'type': 'remove-button', 'index': faculty_result['id'], 'item_type': 'faculty'},
                    style={
                        'height': '40px',
                        'background-color': '#e74c3c',
                        'color': 'white',
                        'border': 'none',
                        'padding': '10px 20px',
                        'text-align': 'center',
                        'text-decoration': 'none',
                        'display': 'inline-block',
                        'font-size': '16px',
                        'margin': '4px 2px',
                        'cursor': 'pointer',
                        'border-radius': '5px'
                    }
                ),
                html.P(f"ID: {faculty_result['id'] or 'N/A'}"),
                html.P(f"Position: {faculty_result['position'] or 'N/A'}"),
                html.P(f"Research Interest: {faculty_result['research_interest'] or 'N/A'}"),
                html.P(f"Email: {faculty_result['email'] or 'N/A'}"),
                html.P(f"Phone: {faculty_result['phone'] or 'N/A'}"),
                html.P(f"Affiliation: {faculty_result['university']}"),
                html.Div(
                    children=[
                        html.Img(src=faculty_result['photo_url'], style={'width': '100px'})
                    ],
                    className='image-container'
                ),
                html.Hr()
            ]))

    if favorite_publications:
        for publication_result in favorite_publications:
            authors = [result['author'] for result in mysql_utils.get_author_by_publication_id(publication_result['id'])]
            if not authors:
                authors = 'N/A'
            favorite_elements.append(html.Div([
                html.H4(f"{publication_result['title']}", style={'display': 'inline-block', 'margin-right': '10px'}),
                html.Button(
                    'Remove from Favorites', 
                    id={'type': 'remove-button', 'index': publication_result['id'], 'item_type': 'publication'},
                    style={
                        'height': '40px',
                        'background-color': '#e74c3c',
                        'color': 'white',
                        'border': 'none',
                        'padding': '10px 20px',
                        'text-align': 'center',
                        'text-decoration': 'none',
                        'display': 'inline-block',
                        'font-size': '16px',
                        'margin': '4px 2px',
                        'cursor': 'pointer',
                        'border-radius': '5px'
                    }
                ),
                html.P(f"ID: {publication_result['id'] or 'N/A'}"),
                html.P(f"Venue: {publication_result['venue'] or 'N/A'}"),
                html.P(f"Year: {publication_result['year'] or 'N/A'}"),
                html.P(f"Number of Citations: {publication_result['num_citations'] or 'N/A'}"),
                html.P(f"Author(s): " + "; ".join([author for author in authors])),
                html.Hr()
            ]))

    return html.Div(favorite_elements)

# Generate colors for node chart
def generate_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def assign_colors(nodes):
    color_map = {}
    for node in nodes:
        color_map[node['id']] = generate_random_color()
    return color_map


# Combined callback to handle the widgets
@app.callback(
    [Output('summary-box', 'children'),
     Output('results-display', 'children'),
     Output('favorites-display', 'children'),
     Output({'type': 'save-button', 'index': ALL, 'item_type': ALL}, 'n_clicks'),
     Output({'type': 'remove-button', 'index': ALL, 'item_type': ALL}, 'n_clicks')],
    [Input('search-button', 'n_clicks'),
     Input('year-range-slider', 'value'),
     Input('keyword-dropdown', 'value'),
     Input({'type': 'save-button', 'index': ALL, 'item_type': ALL}, 'n_clicks'),
     Input('show-favorites-button', 'n_clicks'),
     Input({'type': 'remove-button', 'index': ALL, 'item_type': ALL}, 'n_clicks'),
     Input('faculty-button', 'n_clicks'),
     Input('affiliations-button', 'n_clicks'),
     Input('top-keywords-button', 'n_clicks'),
     Input('calculate-krc-button-action', 'n_clicks')],
    [State({'type': 'save-button', 'index': ALL, 'item_type': ALL}, 'id'),
     State({'type': 'remove-button', 'index': ALL, 'item_type': ALL}, 'id')],
    [State('search-bar', 'value'),
     State('school-name-keyword-input', 'value'),
     State('school-name-krc-input', 'value'),
     State('keyword-krc-input', 'value')]
)

# To check triggers, connect to database and then generate results 
def display_results(search_clicks, year_range, selected_university, save_clicks, show_favorites_click, remove_clicks,
                    faculty_clicks, affiliations_clicks, top_keywords_clicks, calculate_krc_clicks,
                    sids, rids, query, school_name_keyword, school_name_krc, keyword_krc):
    call = dash.callback_context

    if not call.triggered:
        return "Click a button to see results", "Click 'Search' to see results", "Click to see your favorite faculty and publication", save_clicks, remove_clicks

    triggered_input = call.triggered[0]['prop_id'].split('.')[0]

    info_box_content = "Information based on the query results and widget parameters."

    # Extract year range values
    year_min, year_max = year_range

    # Handle year range slider
    if triggered_input == 'year-range-slider':
        year_min, year_max = year_range
        mysql_utils.search_by_year(year_min, year_max)

    # Handle save to favorites buttons
    if save_clicks:
        # Create empty save_clicks as output to refresh save_clicks for each callback
        save_clicks_records = [None] * len(save_clicks)

        for i, n_click in enumerate(save_clicks):
            if n_click:
                item_id = sids[i]['index']
                item_type = sids[i]['item_type']

                save_clicks[i] = None

                if item_type not in ['faculty', 'publication']:
                    return dash.no_update, dash.no_update, dash.no_update, save_clicks, remove_clicks

                if item_type=='faculty':
                    mysql_utils.save_to_favorites_faculty(item_id)
                else:
                    mysql_utils.save_to_favorites_publication(item_id)

                return dash.no_update, dash.no_update, dash.no_update, save_clicks_records, remove_clicks

    # Handle remove from favorites buttons
    if remove_clicks:
        for i, n_click in enumerate(remove_clicks):
            if n_click:
                item_id = rids[i]['index']
                item_type = rids[i]['item_type']

                remove_clicks[i] = None

                if item_type not in ['faculty', 'publication']:
                    return dash.no_update, dash.no_update, dash.no_update, save_clicks, remove_clicks

                if item_type=='faculty':
                    mysql_utils.remove_from_favorites_faculty(item_id)
                else:
                    mysql_utils.remove_from_favorites_publication(item_id)

                return dash.no_update, dash.no_update, show_favorite(), save_clicks, remove_clicks

    # Handle show favorites button
    if triggered_input == 'show-favorites-button':
        return dash.no_update, dash.no_update, show_favorite(), save_clicks, remove_clicks

    # Handle search button
    if triggered_input == 'search-button':
        if not query:
            return dash.no_update, "Please enter a search query and click the search button.", dash.no_update, save_clicks, remove_clicks
        faculty_results = mysql_utils.search_faculty_by_name(query)
        publication_results = mysql_utils.search_publication_by_title(query)

        if not faculty_results and not publication_results:
            return dash.no_update, "No results found.", dash.no_update, save_clicks, remove_clicks
        result_elements = []

        for faculty_result in faculty_results:
            result_elements.append(
                html.Div([
                    html.H4(f"{faculty_result['name']}", style={'margin-right': '5px',}),
                    html.Button(
                        'Save to Favorites', 
                        id={'type': 'save-button', 'index': faculty_result['id'], 'item_type': 'faculty'},
                        style={
                            'height': '40px',
                            'background-color': '#3498db',
                            'color': 'white',
                            'border': 'none',
                            'padding': '10px 20px',
                            'text-align': 'center',
                            'text-decoration': 'none',
                            'display': 'inline-block',
                            'font-size': '16px',
                            'margin': '4px 2px',
                            'cursor': 'pointer',
                            'border-radius': '5px',
                            'margin-left': 'auto',
                        }
                    )
                ], style={'display': 'flex', 'align-items': 'center'})
            )
            result_elements.append(html.P(f"ID: {faculty_result['id'] or 'N/A'}"))
            result_elements.append(html.P(f"Position: {faculty_result['position'] or 'N/A'}"))
            result_elements.append(html.P(f"Research Interest: {faculty_result['research_interest'] or 'N/A'}"))
            result_elements.append(html.P(f"Email: {faculty_result['email'] or 'N/A'}"))
            result_elements.append(html.P(f"Phone: {faculty_result['phone'] or 'N/A'}"))
            result_elements.append(html.P(f"Affiliation: {faculty_result['university']}"))

            # Set photo_url if not valid the CSS show the background image "default_photo.jpg". Not a perfect solution but I tried.
            photo_url = faculty_result['photo_url']
            result_elements.append(html.Div(
                children=[
                    html.Img(src=photo_url, style={'width': '100px'})
                ],
                className='image-container'
            ))

            result_elements.append(html.Hr())

        for publication_result in publication_results:
            authors = [result['author'] for result in mysql_utils.get_author_by_publication_id(publication_result['id'])]
            if not authors:
                authors = 'N/A'
                
            result_elements.append(html.Div([
                html.H4(f"{publication_result['title']}", style={'margin-right': '5px',}),
                html.Button(
                        'Save to Favorites', 
                        id={'type': 'save-button', 'index': publication_result['id'], 'item_type': 'publication'},
                        style={
                            'height': '40px',
                            'background-color': '#3498db',
                            'color': 'white',
                            'border': 'none',
                            'padding': '10px 20px',
                            'text-align': 'center',
                            'text-decoration': 'none',
                            'display': 'inline-block',
                            'font-size': '16px',
                            'margin': '4px 2px',
                            'cursor': 'pointer',
                            'border-radius': '5px',
                            'margin-left': 'auto',
                        }
                    )
            ], style={'display': 'flex', 'align-items': 'center'}))

            result_elements.append(html.P(f"ID: {publication_result['id'] or 'N/A'}"))
            result_elements.append(html.P(f"Venue: {publication_result['venue'] or 'N/A'}"))
            result_elements.append(html.P(f"Year: {publication_result['year'] or 'N/A'}"))
            result_elements.append(html.P(f"Number of Citations: {publication_result['num_citations'] or 'N/A'}"))
            result_elements.append(html.P(f"Author(s): " + "; ".join([author for author in authors])))
            result_elements.append(html.Hr())

        return dash.no_update, html.Div(result_elements), dash.no_update, save_clicks, remove_clicks

    # Handling Tag related buttons
    elif triggered_input == 'faculty-button':
        faculty_count = mongodb_utils.get_faculty_cnt()
        return f"Total number of faculty: {faculty_count}", dash.no_update, dash.no_update, save_clicks, remove_clicks

    elif triggered_input == 'affiliations-button':
        affiliation_count = mongodb_utils.get_affiliation_count()
        affiliations = mongodb_utils.get_all_affiliations()
        affiliations_list = [aff['name'] for aff in affiliations]
        return html.Div([
            html.P(f"Total number of affiliations: {affiliation_count}"),
            html.P("Affiliations:"),
            html.Ul([html.Li(aff) for aff in affiliations_list])
        ]), dash.no_update, dash.no_update, save_clicks, remove_clicks

    elif triggered_input == 'top-keywords-button':
        if not school_name_keyword:
            return "Please enter a school name.", dash.no_update, dash.no_update, save_clicks, remove_clicks
        top_keywords = mongodb_utils.top_keywords_by_school(school_name_keyword)
        if not top_keywords:
            return "No keywords found.", dash.no_update, dash.no_update, save_clicks, remove_clicks
        keywords_list = [html.Li(keyword['_id']) for keyword in top_keywords]
        return html.Ul(keywords_list), dash.no_update, dash.no_update, save_clicks, remove_clicks

    elif triggered_input == 'calculate-krc-button-action':
        if not (school_name_krc and keyword_krc):
            return "Please enter both a school name and a keyword.", dash.no_update, dash.no_update, save_clicks, remove_clicks
        krc_results = mongodb_utils.calculate_krc(school_name_krc, keyword_krc)
        if not krc_results:
            return "No results found.", dash.no_update, dash.no_update, save_clicks, remove_clicks
        krc_elements = [html.Div([html.H4(f"Faculty: {result['_id']}"), html.P(f"KRC: {result['KRC']}")]) for result in krc_results]
        return html.Div(krc_elements), dash.no_update, dash.no_update, save_clicks, remove_clicks

    # Handle keyword-dropdown applications and call REST API
    elif triggered_input == 'keyword-dropdown':
        if selected_university:      
            return display_university_faculty_ratio(selected_university), dash.no_update, dash.no_update, save_clicks, remove_clicks

    return "Unknown action", "Unknown action", dash.no_update, save_clicks, remove_clicks

# REST API to access neo4j database with "GET" method
@server.route('/api/get_university_faculty_ratio', methods=['GET'])
def api_get_university_faculty_ratio():
    university_name = request.args.get('university_name')
    if not university_name:
        return jsonify({"error": "Please provide a university name"}), 400
    try:
        total_faculty_count, university_faculty_count, ratio = neo4j_utils.get_university_faculty_ratio(university_name)
        return jsonify({
            "total_faculty_count": total_faculty_count,
            "university_faculty_count": university_faculty_count,
            "ratio": ratio
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# To calculate KRC
def display_university_faculty_ratio(university_name):
    if university_name:
        try:
            response = requests.get(f'http://localhost:8050/api/get_university_faculty_ratio?university_name={university_name}')
            if response.status_code == 200:
                data = response.json()
                return (f"Total Faculty: {data['total_faculty_count']}, "
                        f"{university_name} Faculty: {data['university_faculty_count']}, "
                        f"Ratio: {data['ratio']:.2%}")
            else:
                return f"An error occurred: {response.json()['error']}"
        except Exception as e:
            return f"An error occurred: {str(e)}"
    return "Please select a university"


# Callback for the Top Cited Publication Graph, WordCloud, and Collab Network
@app.callback(
    [Output('top-cited-publications-graph', 'figure'),
    Output('wordcloud-image', 'src'),
    Output('network-graph', 'elements')],
    [Input('show-publications-button', 'n_clicks')],
    [State('faculty-id-input', 'value')]
)
def update_publications_graphs(n_clicks, faculty_id):
    call = dash.callback_context
    triggered_input = call.triggered[0]['prop_id'].split('.')[0]

    if not call.triggered:
        return go.Figure(), dash.no_update, dash.no_update

    publications = mysql_utils.get_top_cited_publications(faculty_id)
    
    # Generate 
    if triggered_input == 'show-publications-button' and publications:
        name = publications[0]['name']
        titles = [pub['title'] for pub in publications]
        citations = [pub['num_citations'] for pub in publications]

        # Generate unique colors for each bar
        colors = [f'rgba({i * 30 % 255}, {i * 60 % 255}, {i * 90 % 255}, 0.6)' for i in range(len(titles))]

        figure = go.Figure(
            data=[go.Bar(x=list(range(len(titles))), y=citations, marker=dict(color=colors))],
            layout=go.Layout(
                title=f'Top Cited Publications of {name}',
                xaxis={'title': 'Top 5 Publications', 'tickvals': list(range(len(titles))), 'ticktext': list(range(1, len(titles)+1))},
                yaxis={'title': 'Number of Citations'},
                margin={'l': 40, 'b': 100, 't': 40, 'r': 0},
                hovermode='closest'
            )
        )

        # Add hover text to show titles on hover
        figure.update_traces(hovertext=titles, hoverinfo='text+y')

        # Fetch word frequencies from the database
        word_frequencies = mysql_utils.get_research_interest_frequencies(faculty_id)
        if not word_frequencies:
            return dash.no_update, dash.no_update

        wordcloud_image = generate_wordcloud_from_frequencies(dict(word_frequencies))

        # Get faculty nodes and collaborations for the specified faculty member
        faculty_name = mysql_utils.get_faculty_name_from_id(faculty_id)[0]
        faculty_nodes = neo4j_utils.get_faculty_nodes_for_faculty(faculty_name)
        collaborations = neo4j_utils.get_collaborations_for_faculty(faculty_name)

        # Assign colors to nodes
        color_map = assign_colors(faculty_nodes)
        for node in faculty_nodes:
            node['color'] = color_map[node['id']]

        # Create Cytoscape elements
        elements = [{"data": node} for node in faculty_nodes]
        elements += [{"data": 
                      {"source": col['source'], "target": col['target'], "weight": col['weight'], "label": str(col['weight']), "color": color_map[col["target"]]}
                      } for col in collaborations]

        return figure, wordcloud_image, elements  
    else:
        return dash.no_update, dash.no_update, dash.no_update
    


if __name__ == '__main__':
    app.run_server(debug=True)
