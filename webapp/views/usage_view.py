# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Usage data display view.

This module provides functions for visualizing and analyzing usage data metrics.
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
import os
from typing import Optional
import datetime



def display_usage_view(usage_data_path: Optional[str] = None) -> None:
    """
    Display usage data analysis view.

    Args:
        usage_data_path: Path to the usage data JSON file
    """
    if not usage_data_path or not os.path.exists(usage_data_path):
        st.info("No usage data available for this processing session.")
        return
    
    # Load usage data
    try:
        with open(usage_data_path, 'r', encoding='utf-8') as f:
            usage_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        st.error(f"Failed to load usage data: {e}")
        return
    
    # Get cost rates from session state
    # Price defaults are for Amazon Bedrock Data Automation (BDA) and Bedrock API usage of 
    # Amazon Nova Lite Model with on-demand in US East (N. Virginia) region as of 2025-04-01
    # These rates are subject to change, please refer to the official AWS pricing page for the most up-to-date information.
    # https://aws.amazon.com/bedrock/pricing/ 
    cost_per_bda_page = st.session_state.get('cost_per_bda_page', 0.01)
    cost_per_input_token = st.session_state.get('cost_per_input_token', 0.00006)
    cost_per_output_token = st.session_state.get('cost_per_output_token', 0.00024)
    
    # Calculate total costs
    bda_pages = usage_data.get('bda_usage', {}).get('total_pages_processed', 0)
    input_tokens = usage_data.get('bedrock_usage', {}).get('total_input_tokens', 0)
    output_tokens = usage_data.get('bedrock_usage', {}).get('total_output_tokens', 0)
    
    bda_cost = bda_pages * cost_per_bda_page
    input_tokens_cost = (input_tokens / 1000) * cost_per_input_token
    output_tokens_cost = (output_tokens / 1000) * cost_per_output_token
    total_cost = bda_cost + input_tokens_cost + output_tokens_cost
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_time_str = usage_data.get('start_time', '')
        try:
            start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            start_time_formatted = start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            st.metric("Session Start", start_time_formatted)
        except ValueError:
            st.metric("Session Start", "N/A", help="Time when the processing session started")
        
    with col2:
        duration = 'N/A'
        try:
            start_time = usage_data.get('start_time', '')
            start = datetime.datetime.fromisoformat(
                start_time.replace('Z', '+00:00')
            )
            
            end_time = usage_data.get('end_time', '')
            end = datetime.datetime.fromisoformat(
                end_time.replace('Z', '+00:00')
            )
            
            # Format as HH:MM:SS
            duration = str(end - start).split('.', maxsplit=1)[0]
        except Exception:
            pass
        st.metric("Processing Duration", duration, help="Duration of the processing session in HH:MM:SS format")
        
    with col3:
        st.metric("Total Estimated Cost", f"${total_cost:.6f}")
    
    # Create tabs for different metrics
    summary_tab, bda_tab, bedrock_tab, cost_tab = st.tabs(["Summary", "BDA Usage", "Bedrock Usage", "Cost Analysis"])
    
    with summary_tab:
        st.subheader("Usage Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### BDA Usage")
            st.metric("Documents Processed", usage_data.get('bda_usage', {}).get('total_documents_processed', 0))
            st.metric("Pages Processed", bda_pages)
            
        with col2:
            st.markdown("### Bedrock Usage")
            st.metric("Total API Calls", usage_data.get('bedrock_usage', {}).get('total_calls', 0))
            st.metric("Input Tokens", f"{input_tokens:,}")
            st.metric("Output Tokens", f"{output_tokens:,}")
            
    with bda_tab:
        st.subheader("BDA Processing Details")
        
        # Display BDA project ARN
        st.text(f"BDA Project ARN: {usage_data.get('bda_usage', {}).get('project_arn', 'N/A')}")
        
        # Create BDA processing details table
        processing_details = usage_data.get('bda_usage', {}).get('processing_details', [])
        if processing_details:
            df = pd.DataFrame(processing_details)
            
            # Format timestamps
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(
                    lambda x: x.replace('T', ' ').replace('Z', ' UTC') if isinstance(x, str) else x
                )
            
            st.dataframe(df)
            
            # Create page distribution chart
            if 'pages' in df.columns:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X('document_id:N', title='Document ID'),
                    y=alt.Y('pages:Q', title='Pages'),
                    tooltip=['document_id', 'pages']
                ).properties(
                    title='Pages per Document',
                    height=300
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No BDA processing details available.")
            
    with bedrock_tab:
        st.subheader("Bedrock API Usage")
        
        # Display usage by model
        st.markdown("### Usage by Model")
        model_usage = usage_data.get('bedrock_usage', {}).get('calls_by_model', {})
        if model_usage:
            model_df = pd.DataFrame([
                {
                    'Model': model_id,
                    'Calls': data.get('total_calls', 0),
                    'Input Tokens': data.get('input_tokens', 0),
                    'Output Tokens': data.get('output_tokens', 0),
                }
                for model_id, data in model_usage.items()
            ])
            
            st.dataframe(model_df)
            
            # Create model usage chart
            chart = alt.Chart(model_df).mark_bar().encode(
                x=alt.X('Model:N', title='Model'),
                y=alt.Y('sum(Input Tokens):Q', title='Total Tokens'),
                color=alt.Color('Model:N', legend=None)
            ).properties(
                title='Input Tokens by Model',
                height=300
            ) + alt.Chart(model_df).mark_bar().encode(
                x=alt.X('Model:N', title='Model'),
                y=alt.Y('sum(Output Tokens):Q', title='Total Tokens'),
                color=alt.Color('Model:N', legend=None)
            ).properties(
                title='Output Tokens by Model',
                height=300
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No model usage data available.")
        
        # Display usage by purpose
        st.markdown("### Usage by Purpose")
        purpose_usage = usage_data.get('bedrock_usage', {}).get('calls_by_purpose', {})
        if purpose_usage:
            purpose_df = pd.DataFrame([
                {
                    'Purpose': purpose,
                    'Calls': data.get('total_calls', 0),
                    'Input Tokens': data.get('input_tokens', 0),
                    'Output Tokens': data.get('output_tokens', 0),
                }
                for purpose, data in purpose_usage.items()
            ])
            
            st.dataframe(purpose_df)
            
            # Create purpose tokens chart
            melted_df = pd.melt(
                purpose_df, 
                id_vars=['Purpose'], 
                value_vars=['Input Tokens', 'Output Tokens'],
                var_name='Token Type', 
                value_name='Tokens'
            )
            
            chart = alt.Chart(melted_df).mark_bar().encode(
                x=alt.X('Purpose:N', title='Purpose'),
                y=alt.Y('Tokens:Q', title='Tokens'),
                color=alt.Color('Token Type:N'),
                tooltip=['Purpose', 'Token Type', 'Tokens']
            ).properties(
                title='Token Usage by Purpose',
                height=300
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No purpose usage data available.")
        
        # Display call details
        st.markdown("### API Call Details")
        call_details = usage_data.get('bedrock_usage', {}).get('call_details', [])
        if call_details:
            df = pd.DataFrame(call_details)
            
            # Format timestamps
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(
                    lambda x: x.replace('T', ' ').replace('Z', ' UTC') if isinstance(x, str) else x
                )
            
            st.dataframe(df)
        else:
            st.info("No call details available.")
    
    with cost_tab:
        st.subheader("Cost Analysis")
        
        # Display cost breakdown
        cost_data = {
            'Category': ['BDA Pages', 'Input Tokens', 'Output Tokens', 'Total'],
            'Usage': [bda_pages, input_tokens, output_tokens, '-'],
            'Rate': [
                f"${cost_per_bda_page:.6f} per page", 
                f"${cost_per_input_token:.6f} per 1K tokens", 
                f"${cost_per_output_token:.6f} per 1K tokens",
                '-'
            ],
            'Cost': [bda_cost, input_tokens_cost, output_tokens_cost, total_cost]
        }
        
        cost_df = pd.DataFrame(cost_data)
        cost_df['Cost'] = cost_df['Cost'].apply(lambda x: f"${x:.6f}")
        
        st.dataframe(cost_df, use_container_width=True)
        
        # Create cost breakdown chart
        chart_data = {
            'Category': ['BDA Pages', 'Input Tokens', 'Output Tokens'],
            'Cost': [bda_cost, input_tokens_cost, output_tokens_cost]
        }
        chart_df = pd.DataFrame(chart_data)
        
        chart = alt.Chart(chart_df).mark_arc().encode(
            theta=alt.Theta(field="Cost", type="quantitative"),
            color=alt.Color(field="Category", type="nominal"),
            tooltip=['Category', alt.Tooltip('Cost:Q', format='$.6f')]
        ).properties(
            title='Cost Distribution',
            height=300
        )
        st.altair_chart(chart, use_container_width=True)
        
        # Display cost by purpose
        st.markdown("### Cost by Purpose")
        purpose_usage = usage_data.get('bedrock_usage', {}).get('calls_by_purpose', {})
        if purpose_usage:
            purpose_cost_data = []
            for purpose, data in purpose_usage.items():
                input_t = data.get('input_tokens', 0)
                output_t = data.get('output_tokens', 0)
                input_cost = (input_t / 1000) * cost_per_input_token
                output_cost = (output_t / 1000) * cost_per_output_token
                total_purpose_cost = input_cost + output_cost
                
                purpose_cost_data.append({
                    'Purpose': purpose,
                    'Input Tokens': input_t,
                    'Output Tokens': output_t,
                    'Input Cost': input_cost,
                    'Output Cost': output_cost,
                    'Total Cost': total_purpose_cost
                })
            
            purpose_cost_df = pd.DataFrame(purpose_cost_data)
            # Format cost columns
            for col in ['Input Cost', 'Output Cost', 'Total Cost']:
                purpose_cost_df[col] = purpose_cost_df[col].apply(lambda x: f"${x:.6f}")
            
            st.dataframe(purpose_cost_df, use_container_width=True)
            
            # Create cost by purpose chart
            chart_df = pd.DataFrame([
                {
                    'Purpose': d['Purpose'],
                    'Cost': d['Input Cost'].replace('$', '') if isinstance(d['Input Cost'], str) else d['Input Cost'],
                    'Type': 'Input'
                } for d in purpose_cost_data
            ] + [
                {
                    'Purpose': d['Purpose'],
                    'Cost': d['Output Cost'].replace('$', '') if isinstance(d['Output Cost'], str) else d['Output Cost'],
                    'Type': 'Output'
                } for d in purpose_cost_data
            ])
            
            # Convert Cost column to float
            chart_df['Cost'] = chart_df['Cost'].astype(float)
            
            chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('Purpose:N', title='Purpose'),
                y=alt.Y('Cost:Q', title='Cost ($)'),
                color=alt.Color('Type:N'),
                tooltip=['Purpose', 'Type', alt.Tooltip('Cost:Q', format='$.6f')]
            ).properties(
                title='Cost by Purpose',
                height=300
            )
            st.altair_chart(chart, use_container_width=True)
